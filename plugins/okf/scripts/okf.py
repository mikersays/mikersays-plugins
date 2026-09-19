#!/usr/bin/env python3
"""okf.py -- validate, index, and log Open Knowledge Format (OKF v0.2) bundles.

Stdlib only, single file, Python 3.9+. Bundles a small YAML-subset parser so
it runs anywhere; PyYAML is used as a fallback only when present and only
when the built-in parser gives up on a frontmatter block.

Usage
-----
    python3 okf.py validate BUNDLE [--strict] [--json] [--now ISO-8601]
    python3 okf.py index    BUNDLE [--write | --check]
    python3 okf.py log      BUNDLE "entry text" [--kind Update] [--date YYYY-MM-DD] [--dir SUBDIR]
    python3 okf.py --selftest

validate  Reports conformance errors (E...) and lint warnings (W...) against
          OKF v0.2 (https://github.com/GoogleCloudPlatform/open-knowledge-format),
          then a trust/lifecycle summary. Exit 1 on any error, or on any
          warning under --strict. --now pins "now" for staleness checks.
index     Regenerates every index.md from frontmatter: subdirectories first,
          then one section per concept `type`, entries sorted by title, with
          descriptions taken from frontmatter (falling back to whatever the
          existing index.md said). Default is a dry run that prints unified
          diffs. --write applies; --check exits 1 if anything is out of date.
log       Prepends a dated entry to log.md (newest first, ISO date headings),
          creating the file if needed.

Exit codes: 0 clean, 1 findings / out of date / selftest failure, 2 usage or IO error.

Finding format:  path[:line]: CODE message
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

__version__ = "0.2.0"

RESERVED = {"index.md", "log.md"}
STATUSES = {"draft", "stable", "deprecated"}
OKF_VERSION = "0.2"

TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})$"
)
ACTOR_RE = re.compile(r"^(?:[A-Za-z0-9_.-]+:[^\s]+|[^\s/:]+/[^\s]+)$")
DATE_HEADING_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*$")
URL_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FOOTNOTE_USE_RE = re.compile(r"\[\^([^\]\s]+)\](?!:)")
FOOTNOTE_DEF_RE = re.compile(r"^\[\^([^\]\s]+)\]:")
INDEX_ENTRY_RE = re.compile(
    r"^\s*[*+-]\s+\[([^\]]*)\]\(([^)\s]+)\)\s*(?:[-\u2013\u2014:]\s*(.*))?$"
)
FENCE_RE = re.compile(r"^\s*(```|~~~)")


# ---------------------------------------------------------------------------
# YAML subset parser
# ---------------------------------------------------------------------------

class YAMLError(ValueError):
    pass


def _strip_comment(line: str) -> str:
    out = []
    quote: Optional[str] = None
    for i, ch in enumerate(line):
        if quote:
            out.append(ch)
            if ch == quote and (quote == "'" or line[i - 1] != "\\"):
                quote = None
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        else:
            out.append(ch)
    return "".join(out).rstrip()


def _split_key(text: str):
    """Return (key, rest) when text is `key: rest` with the colon outside quotes."""
    if not text:
        return None
    if text[0] in "\"'":
        q = text[0]
        j = text.find(q, 1)
        if j > 0 and text[j + 1: j + 2] == ":" and (len(text) == j + 2 or text[j + 2] in " \t"):
            return text[1:j], text[j + 2:].strip()
        return None
    if text[0] in "{[":
        return None
    for i, ch in enumerate(text):
        if ch == ":" and (i + 1 == len(text) or text[i + 1] in " \t"):
            return text[:i].strip(), text[i + 1:].strip()
        if ch in "{[\"'":
            return None
    return None


def _unescape(s: str) -> str:
    return (
        s.replace("\\\"", "\"").replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\")
    )


def _scalar(s: str) -> Any:
    s = s.strip()
    if s == "":
        return None
    if len(s) >= 2 and s[0] == "\"" and s[-1] == "\"":
        return _unescape(s[1:-1])
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return s[1:-1].replace("''", "'")
    low = s.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    if low in ("null", "~"):
        return None
    if re.fullmatch(r"[-+]?\d+", s):
        return int(s)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?", s):
        return float(s)
    return s


def _flow_token(s: str, pos: int, stops: str, lineno: int):
    n = len(s)
    if pos < n and s[pos] in "\"'":
        q = s[pos]
        j = pos + 1
        while j < n:
            if s[j] == q and (q == "'" or s[j - 1] != "\\"):
                return s[pos: j + 1], j + 1
            j += 1
        raise YAMLError(f"line {lineno}: unterminated quote")
    j = pos
    while j < n and s[j] not in stops:
        j += 1
    return s[pos:j].strip(), j


def _parse_flow(s: str, pos: int, lineno: int):
    n = len(s)

    def ws(p: int) -> int:
        while p < n and s[p] in " \t":
            p += 1
        return p

    pos = ws(pos)
    if pos >= n:
        raise YAMLError(f"line {lineno}: empty flow value")
    if s[pos] == "{":
        pos += 1
        d: dict = {}
        while True:
            pos = ws(pos)
            if pos >= n:
                raise YAMLError(f"line {lineno}: unterminated '{{'")
            if s[pos] == "}":
                return d, pos + 1
            key_raw, pos = _flow_token(s, pos, ":,}", lineno)
            pos = ws(pos)
            if pos >= n or s[pos] != ":":
                raise YAMLError(f"line {lineno}: expected ':' in flow mapping")
            pos = ws(pos + 1)
            if pos < n and s[pos] in "{[":
                val, pos = _parse_flow(s, pos, lineno)
            else:
                raw, pos = _flow_token(s, pos, ",}", lineno)
                val = _scalar(raw)
            d[str(_scalar(key_raw))] = val
            pos = ws(pos)
            if pos < n and s[pos] == ",":
                pos += 1
                continue
            if pos < n and s[pos] == "}":
                return d, pos + 1
            raise YAMLError(f"line {lineno}: expected ',' or '}}' in flow mapping")
    if s[pos] == "[":
        pos += 1
        items: list = []
        while True:
            pos = ws(pos)
            if pos >= n:
                raise YAMLError(f"line {lineno}: unterminated '['")
            if s[pos] == "]":
                return items, pos + 1
            if s[pos] in "{[":
                val, pos = _parse_flow(s, pos, lineno)
            else:
                raw, pos = _flow_token(s, pos, ",]", lineno)
                val = _scalar(raw)
            items.append(val)
            pos = ws(pos)
            if pos < n and s[pos] == ",":
                pos += 1
                continue
            if pos < n and s[pos] == "]":
                return items, pos + 1
            raise YAMLError(f"line {lineno}: expected ',' or ']' in flow list")
    raise YAMLError(f"line {lineno}: bad flow value")


def _parse_inline(rest: str, lineno: int) -> Any:
    rest = rest.strip()
    if rest[:1] in ("{", "["):
        val, pos = _parse_flow(rest, 0, lineno)
        if rest[pos:].strip():
            raise YAMLError(f"line {lineno}: trailing content after flow value")
        return val
    return _scalar(rest)


def _parse_block_scalar(lines, i, indent, style):
    parts = []
    while i < len(lines) and lines[i][0] > indent:
        parts.append(lines[i][1])
        i += 1
    sep = "\n" if style.startswith("|") else " "
    text = sep.join(parts)
    if not style.endswith("-"):
        text += "\n"
    return text, i


def _parse_map(lines, i, indent):
    result: dict = {}
    while i < len(lines) and lines[i][0] == indent:
        _, text, n, _ = lines[i]
        if text == "-" or text.startswith("- "):
            raise YAMLError(f"line {n}: sequence item where a mapping key was expected")
        kv = _split_key(text)
        if kv is None:
            raise YAMLError(f"line {n}: expected 'key: value'")
        key, rest = kv
        i += 1
        if rest == "":
            if i < len(lines) and lines[i][0] > indent:
                val, i = _parse_block(lines, i, lines[i][0])
            elif i < len(lines) and lines[i][0] == indent and (
                lines[i][1] == "-" or lines[i][1].startswith("- ")
            ):
                val, i = _parse_seq(lines, i, indent)
            else:
                val = None
        elif rest in ("|", ">", "|-", ">-", "|+", ">+"):
            val, i = _parse_block_scalar(lines, i, indent, rest)
        else:
            val = _parse_inline(rest, n)
        result[key] = val
    if i < len(lines) and lines[i][0] > indent:
        raise YAMLError(f"line {lines[i][2]}: bad indentation")
    return result, i


def _parse_seq(lines, i, indent):
    result: list = []
    while i < len(lines) and lines[i][0] == indent and (
        lines[i][1] == "-" or lines[i][1].startswith("- ")
    ):
        ind, text, n, raw = lines[i]
        rest = text[1:].strip()
        if rest == "":
            i += 1
            if i < len(lines) and lines[i][0] > indent:
                val, i = _parse_block(lines, i, lines[i][0])
            else:
                val = None
        elif rest[:1] not in ("{", "[") and _split_key(rest) is not None:
            col = ind + len(text) - len(rest)
            lines[i] = [col, rest, n, raw]
            val, i = _parse_map(lines, i, col)
        else:
            val = _parse_inline(rest, n)
            i += 1
        result.append(val)
    return result, i


def _parse_block(lines, i, indent):
    if lines[i][0] != indent:
        raise YAMLError(f"line {lines[i][2]}: bad indentation")
    if lines[i][1] == "-" or lines[i][1].startswith("- "):
        return _parse_seq(lines, i, indent)
    return _parse_map(lines, i, indent)


def parse_yaml(src: str) -> dict:
    """Parse the YAML subset used by OKF frontmatter into plain Python values."""
    lines = []
    for n, raw in enumerate(src.split("\n"), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        text = _strip_comment(raw)
        if not text.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append([indent, text.strip(), n, raw])
    if not lines:
        return {}
    try:
        val, i = _parse_block(lines, 0, lines[0][0])
        if i != len(lines):
            raise YAMLError(f"line {lines[i][2]}: unexpected content")
    except YAMLError:
        val = _pyyaml_fallback(src)
        if val is None:
            raise
    if not isinstance(val, dict):
        raise YAMLError("frontmatter is not a mapping")
    return val


def _pyyaml_fallback(src: str):
    try:
        import yaml  # type: ignore
    except Exception:
        return None
    try:
        val = yaml.safe_load(src)
    except Exception:
        return None

    def norm(v):
        if isinstance(v, dict):
            return {str(k): norm(x) for k, x in v.items()}
        if isinstance(v, list):
            return [norm(x) for x in v]
        if isinstance(v, datetime):
            return v.isoformat().replace("+00:00", "Z")
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return v

    return norm(val) if isinstance(val, dict) else None


# ---------------------------------------------------------------------------
# Document model
# ---------------------------------------------------------------------------

def split_frontmatter(text: str):
    """Return (frontmatter_text | None, body, body_start_line, error | None)."""
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text, 1, None
    for j in range(1, len(lines)):
        if lines[j].strip() in ("---", "..."):
            return "\n".join(lines[1:j]), "\n".join(lines[j + 1:]), j + 2, None
    return None, text, 1, "unterminated frontmatter block"


class Doc:
    def __init__(self, bundle: Path, path: Path):
        self.bundle = bundle
        self.path = path
        self.rel = path.relative_to(bundle).as_posix()
        self.text = path.read_text(encoding="utf-8", errors="replace")
        self.fm_text, self.body, self.body_line, self.fm_error = split_frontmatter(self.text)
        self.fm: Optional[dict] = None
        self.parse_error: Optional[str] = None
        if self.fm_text is not None:
            try:
                self.fm = parse_yaml(self.fm_text)
            except YAMLError as exc:
                self.parse_error = str(exc)

    @property
    def is_reserved(self) -> bool:
        return self.path.name in RESERVED

    @property
    def concept_id(self) -> str:
        return self.rel[:-3] if self.rel.endswith(".md") else self.rel


def iter_md(bundle: Path):
    for p in sorted(bundle.rglob("*.md")):
        if any(part.startswith(".") for part in p.relative_to(bundle).parts):
            continue
        yield p


def is_hidden(p: Path, bundle: Path) -> bool:
    return any(part.startswith(".") for part in p.relative_to(bundle).parts)


def resolve_path(bundle: Path, from_file: Path, target: str) -> Optional[Path]:
    """Resolve a bundle-relative (/x) or relative path; None for URLs/anchors."""
    if not target or target.startswith("#") or URL_RE.match(target):
        return None
    target = target.split("#", 1)[0]
    if target.startswith("/"):
        return (bundle / target.lstrip("/")).resolve()
    return (from_file.parent / target).resolve()


def field_path_exists(bundle: Path, from_file: Path, target: str) -> Optional[bool]:
    """Existence of a path-valued frontmatter field. Relative paths are tried
    against the file's directory and then the bundle root, since producers in
    the wild write `references/x.md` meaning bundle-root-relative. None for URLs."""
    resolved = resolve_path(bundle, from_file, target)
    if resolved is None:
        return None
    if resolved.exists():
        return True
    if not target.startswith("/"):
        return (bundle / target.split("#", 1)[0]).exists()
    return False


def looks_like_path(value: str) -> bool:
    return bool(value) and " " not in value.strip() and not URL_RE.match(value)


def parse_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not TIMESTAMP_RE.match(value):
        return None
    s = value.replace("Z", "+00:00")
    m = re.match(r"^(.*[+-]\d{2})(\d{2})$", s)
    if m:
        s = f"{m.group(1)}:{m.group(2)}"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def as_list(v: Any) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def trust_tier(fm: dict) -> str:
    entries = as_list(fm.get("verified"))
    if not entries:
        return "unverified"
    for e in entries:
        by = e.get("by") if isinstance(e, dict) else None
        if isinstance(by, str) and by.startswith("human:"):
            return "human-reviewed"
    return "machine-confirmed"


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

class Finding:
    def __init__(self, path: str, code: str, message: str, line: Optional[int] = None):
        self.path = path
        self.code = code
        self.message = message
        self.line = line

    @property
    def level(self) -> str:
        return "error" if self.code.startswith("E") else "warning"

    def __str__(self) -> str:
        loc = f"{self.path}:{self.line}" if self.line else self.path
        return f"{loc}: {self.code} {self.message}"

    def as_dict(self) -> dict:
        return {
            "path": self.path, "line": self.line, "code": self.code,
            "level": self.level, "message": self.message,
        }


def body_lines_outside_fences(body: str, start_line: int):
    in_fence = False
    fence_mark = ""
    for offset, line in enumerate(body.split("\n")):
        m = FENCE_RE.match(line)
        if m:
            mark = m.group(1)
            if not in_fence:
                in_fence, fence_mark = True, mark
            elif mark == fence_mark:
                in_fence = False
            continue
        if not in_fence:
            yield start_line + offset, line


def body_has_computation_fence(body: str) -> bool:
    lines = body.split("\n")
    under = False
    for line in lines:
        if re.match(r"^#{1,6}\s+", line):
            under = bool(re.match(r"^#{1,6}\s+Computation\s*$", line))
            continue
        if under and (FENCE_RE.match(line) or line.startswith("    ")):
            return True
    return False


def validate_bundle(bundle: Path, now: datetime) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    docs: dict[str, Doc] = {}
    summary = {
        "concepts": 0, "types": {}, "trust": {}, "status": {}, "stale": 0,
        "attested_computations": 0, "okf_version": None,
    }

    def add(path: str, code: str, msg: str, line: Optional[int] = None):
        findings.append(Finding(path, code, msg, line))

    for p in iter_md(bundle):
        doc = Doc(bundle, p)
        docs[doc.rel] = doc

    for rel, doc in docs.items():
        if doc.is_reserved:
            if doc.path.name == "index.md":
                _check_index(bundle, doc, docs, add, summary)
            else:
                _check_log(doc, add)
            continue

        summary["concepts"] += 1
        if doc.fm_error:
            add(rel, "E002", doc.fm_error, 1)
            continue
        if doc.fm_text is None:
            add(rel, "E001", "no YAML frontmatter block (every concept needs one)", 1)
            continue
        if doc.parse_error:
            add(rel, "E002", f"frontmatter does not parse: {doc.parse_error}", 1)
            continue
        fm = doc.fm or {}
        _check_concept(bundle, doc, fm, docs, add, now, summary)

    # Directories with concepts but no index.md
    dirs = set()
    for doc in docs.values():
        dirs.add(doc.path.parent)
    for d in sorted(dirs):
        if not (d / "index.md").exists():
            rel = d.relative_to(bundle).as_posix() or "."
            add(f"{rel}/index.md" if rel != "." else "index.md", "W120",
                "no index.md in this directory (run `okf.py index --write` to generate one)")

    return findings, summary


def _check_concept(bundle, doc: Doc, fm: dict, docs, add, now, summary):
    rel = doc.rel
    ctype = fm.get("type")
    if not isinstance(ctype, str) or not ctype.strip():
        add(rel, "E003", "frontmatter has no non-empty `type` (the only required key)", 1)
    else:
        summary["types"][ctype] = summary["types"].get(ctype, 0) + 1

    if not fm.get("description"):
        add(rel, "W101", "no `description` (recommended; index.md entries and previews use it)", 1)

    # Lifecycle
    status = fm.get("status", "stable")
    if status not in STATUSES:
        add(rel, "W105", f"`status` is {status!r}; expected one of draft | stable | deprecated", 1)
        status = "stable"
    summary["status"][status] = summary["status"].get(status, 0) + 1

    if "stale_after" in fm:
        ts = parse_timestamp(fm["stale_after"])
        if ts is None:
            add(rel, "W102", f"`stale_after` is not an ISO 8601 datetime with UTC offset: {fm['stale_after']!r}", 1)
        elif now >= ts:
            summary["stale"] += 1
            add(rel, "W106", f"stale: `stale_after` {fm['stale_after']} has passed; re-verify before serving", 1)

    # Trust
    if "timestamp" in fm and "generated" not in fm:
        add(rel, "W118", "legacy v0.1 `timestamp`; v0.2 records this as `generated: { by, at }`", 1)
    gen = fm.get("generated")
    if gen is not None:
        if not isinstance(gen, dict):
            add(rel, "W104", "`generated` must be a mapping `{ by, at }`", 1)
        else:
            by = gen.get("by")
            if not by:
                add(rel, "W104", "`generated` has no `by` (required within `generated`)", 1)
            elif not isinstance(by, str) or not ACTOR_RE.match(by):
                add(rel, "W103", f"`generated.by` {by!r} does not follow the actor convention (<producer>/<version>, human:<id>, process:<id>)", 1)
            if "at" in gen and parse_timestamp(gen.get("at")) is None:
                add(rel, "W102", f"`generated.at` is not an ISO 8601 datetime with UTC offset: {gen.get('at')!r}", 1)
    for i, entry in enumerate(as_list(fm.get("verified"))):
        if not isinstance(entry, dict):
            add(rel, "W116", f"`verified[{i}]` must be a mapping `{{ by, at }}`", 1)
            continue
        by, at = entry.get("by"), entry.get("at")
        if not by:
            add(rel, "W116", f"`verified[{i}]` has no `by`", 1)
        elif not isinstance(by, str) or not ACTOR_RE.match(by):
            add(rel, "W103", f"`verified[{i}].by` {by!r} does not follow the actor convention", 1)
        if at is None:
            add(rel, "W116", f"`verified[{i}]` has no `at`", 1)
        elif parse_timestamp(at) is None:
            add(rel, "W102", f"`verified[{i}].at` is not an ISO 8601 datetime with UTC offset: {at!r}", 1)
    tier = trust_tier(fm)
    summary["trust"][tier] = summary["trust"].get(tier, 0) + 1

    # Provenance
    source_ids: set[str] = set()
    sources = fm.get("sources")
    if sources is not None and not isinstance(sources, list):
        add(rel, "W107", "`sources` must be a list of entries", 1)
        sources = []
    has_usage_count = False
    for i, src in enumerate(sources or []):
        if not isinstance(src, dict):
            add(rel, "W107", f"`sources[{i}]` must be a mapping", 1)
            continue
        res = src.get("resource")
        if not res:
            add(rel, "W107", f"`sources[{i}]` has no `resource` (required within an entry)", 1)
        elif isinstance(res, str) and looks_like_path(res) and "/" in res:
            if field_path_exists(bundle, doc.path, res) is False:
                add(rel, "W111", f"`sources[{i}].resource` path does not exist in the bundle: {res}", 1)
        sid = src.get("id")
        if sid:
            source_ids.add(str(sid))
        author = src.get("author")
        if author and (not isinstance(author, str) or not ACTOR_RE.match(author)):
            add(rel, "W103", f"`sources[{i}].author` {author!r} does not follow the actor convention", 1)
        if "last_modified" in src and parse_timestamp(src["last_modified"]) is None:
            add(rel, "W102", f"`sources[{i}].last_modified` is not an ISO 8601 datetime with UTC offset", 1)
        if "usage_count" in src:
            has_usage_count = True
            if "usage_window" in src:
                _check_window(rel, src["usage_window"], f"sources[{i}].usage_window", add)
    if "usage_window" in fm:
        _check_window(rel, fm["usage_window"], "usage_window", add)
    elif has_usage_count and not any(
        isinstance(s, dict) and "usage_window" in s for s in (sources or [])
    ):
        add(rel, "W119", "`usage_count` present but no `usage_window` frames it", 1)

    # Body: footnotes, links, legacy citations
    seen_labels: dict[str, int] = {}
    for lineno, line in body_lines_outside_fences(doc.body, doc.body_line):
        if re.match(r"^#{1,6}\s+Citations\s*$", line):
            add(rel, "W118", "legacy v0.1 `# Citations` list; v0.2 records provenance in `sources`", lineno)
        for m in FOOTNOTE_DEF_RE.finditer(line):
            seen_labels.setdefault(m.group(1), lineno)
        for m in FOOTNOTE_USE_RE.finditer(line):
            seen_labels.setdefault(m.group(1), lineno)
        for m in LINK_RE.finditer(line):
            target = m.group(1)
            resolved = resolve_path(bundle, doc.path, target)
            if resolved is None:
                continue
            if not resolved.exists():
                add(rel, "W110", f"link target does not exist in the bundle: {target}", lineno)
    for label, lineno in seen_labels.items():
        if label not in source_ids:
            add(rel, "W108", f"footnote [^{label}] has no matching `sources[].id` (the label is the join key)", lineno)

    # Path-valued fields
    for field in ("computation",):
        val = fm.get(field)
        if isinstance(val, str) and looks_like_path(val):
            if field_path_exists(bundle, doc.path, val) is False:
                add(rel, "W111", f"`{field}` path does not exist in the bundle: {val}", 1)
    for family in ("executor", "attester"):
        val = fm.get(family)
        if isinstance(val, dict):
            res = val.get("resource")
            if isinstance(res, str) and looks_like_path(res):
                if field_path_exists(bundle, doc.path, res) is False:
                    add(rel, "W111", f"`{family}.resource` path does not exist in the bundle: {res}", 1)

    # Attested Computation contract
    if isinstance(ctype, str) and ctype.strip().lower() == "attested computation":
        summary["attested_computations"] += 1
        if not fm.get("runtime"):
            add(rel, "E006", "Attested Computation has no `runtime` (required for this type)", 1)
        has_fence = body_has_computation_fence(doc.body)
        has_file = bool(fm.get("computation"))
        if not has_fence and not has_file:
            add(rel, "W112", "Attested Computation has neither a `# Computation` fence in the body nor a `computation` file path", 1)
        elif has_fence and has_file:
            add(rel, "W112", "Attested Computation has both a `# Computation` fence and a `computation` path; pick one", 1)
        params = fm.get("parameters")
        if params is not None:
            if not isinstance(params, list):
                add(rel, "W113", "`parameters` must be a list of `{ name, type, required }`", 1)
            else:
                for i, prm in enumerate(params):
                    if not isinstance(prm, dict) or not prm.get("name") or not prm.get("type"):
                        add(rel, "W113", f"`parameters[{i}]` needs at least `name` and `type`", 1)
        ex = fm.get("executor")
        if ex is not None and (not isinstance(ex, dict) or not ex.get("resource")):
            add(rel, "W113", "`executor` needs a `resource` naming run instructions or code", 1)
        elif isinstance(ex, dict) and not ex.get("receipt"):
            add(rel, "W113", "`executor` has no `receipt` list; the attester has nothing to inspect", 1)
        at = fm.get("attester")
        if at is not None and (not isinstance(at, dict) or not at.get("resource")):
            add(rel, "W113", "`attester` needs a `resource` naming deterministic verification code", 1)


def _check_window(rel, window, label, add):
    if not isinstance(window, dict):
        add(rel, "W102", f"`{label}` must be `{{ from, to }}`", 1)
        return
    for k in ("from", "to"):
        if parse_timestamp(window.get(k)) is None:
            add(rel, "W102", f"`{label}.{k}` is not an ISO 8601 datetime with UTC offset", 1)


def _check_index(bundle, doc: Doc, docs, add, summary):
    rel = doc.rel
    is_root = doc.path.parent == bundle
    if doc.fm_error:
        add(rel, "E004", doc.fm_error, 1)
    elif doc.fm_text is not None:
        if not is_root:
            add(rel, "E004", "index.md must not carry frontmatter (only the bundle-root index may, for `okf_version`)", 1)
        elif doc.parse_error:
            add(rel, "E004", f"root index.md frontmatter does not parse: {doc.parse_error}", 1)
        else:
            extra = sorted(k for k in (doc.fm or {}) if k != "okf_version")
            if extra:
                add(rel, "E004", f"root index.md frontmatter may only carry `okf_version`, found: {', '.join(extra)}", 1)
            ver = (doc.fm or {}).get("okf_version")
            if ver is not None:
                summary["okf_version"] = str(ver)
                if str(ver) != OKF_VERSION:
                    add(rel, "W117", f"`okf_version` is {ver!r}; this validator targets {OKF_VERSION}", 1)
    elif is_root:
        add(rel, "W117", f"root index.md does not declare `okf_version: \"{OKF_VERSION}\"`", 1)

    linked: set[Path] = set()
    for lineno, line in body_lines_outside_fences(doc.body, doc.body_line):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = INDEX_ENTRY_RE.match(line)
        if not m:
            if re.match(r"^\s*[*+-]\s", line):
                add(rel, "W114", "index entry is not `* [Title](url) - description`", lineno)
            continue
        target = m.group(2)
        resolved = resolve_path(bundle, doc.path, target)
        if resolved is None:
            continue
        if resolved.is_dir():
            linked.add(resolved)
            linked.add(resolved / "index.md")
        elif resolved.exists():
            linked.add(resolved)
            if resolved.name == "index.md":
                linked.add(resolved.parent)
        else:
            add(rel, "W114", f"index entry points at a missing target: {target}", lineno)

    d = doc.path.parent
    for child in sorted(d.iterdir()):
        if is_hidden(child, bundle):
            continue
        if child.is_dir():
            if any(True for _ in child.rglob("*.md")) and child.resolve() not in {p.resolve() for p in linked}:
                add(rel, "W115", f"subdirectory not listed in index: {child.name}/", None)
        elif child.suffix == ".md" and child.name not in RESERVED:
            if child.resolve() not in {p.resolve() for p in linked}:
                add(rel, "W115", f"concept not listed in index: {child.name}", None)


def _check_log(doc: Doc, add):
    rel = doc.rel
    if doc.fm_error:
        add(rel, "E005", doc.fm_error, 1)
        return
    if doc.parse_error:
        add(rel, "E005", f"log.md frontmatter does not parse: {doc.parse_error}", 1)
    last: Optional[str] = None
    for lineno, line in body_lines_outside_fences(doc.body, doc.body_line):
        if line.startswith("## "):
            m = DATE_HEADING_RE.match(line)
            if not m:
                add(rel, "E005", f"log.md `##` headings must be ISO dates (YYYY-MM-DD): {line.strip()!r}", lineno)
                continue
            date = m.group(1)
            try:
                datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                add(rel, "E005", f"log.md heading is not a real date: {date}", lineno)
                continue
            if last is not None and date > last:
                add(rel, "W121", f"log.md entries should be newest first; {date} appears after {last}", lineno)
            last = date


def cmd_validate(args) -> int:
    bundle = Path(args.bundle).resolve()
    if not bundle.is_dir():
        print(f"error: not a directory: {args.bundle}", file=sys.stderr)
        return 2
    now = parse_timestamp(args.now) if args.now else datetime.now(timezone.utc)
    if now is None:
        print("error: --now must be an ISO 8601 datetime with UTC offset", file=sys.stderr)
        return 2
    findings, summary = validate_bundle(bundle, now)
    findings.sort(key=lambda f: (f.path, f.line or 0, f.code))
    errors = [f for f in findings if f.level == "error"]
    warnings = [f for f in findings if f.level == "warning"]
    if args.json:
        print(json.dumps({
            "bundle": str(bundle), "findings": [f.as_dict() for f in findings],
            "errors": len(errors), "warnings": len(warnings), "summary": summary,
        }, indent=2))
    else:
        for f in findings:
            print(f)
        if findings:
            print()
        print(f"OKF {OKF_VERSION} check of {bundle}")
        print(f"  concepts: {summary['concepts']}"
              + (f"  (declared okf_version {summary['okf_version']})" if summary["okf_version"] else "  (no okf_version declared)"))
        if summary["types"]:
            print("  types:    " + ", ".join(f"{k} x{v}" for k, v in sorted(summary["types"].items())))
        if summary["trust"]:
            print("  trust:    " + ", ".join(f"{k} {v}" for k, v in sorted(summary["trust"].items())))
        if summary["status"]:
            print("  status:   " + ", ".join(f"{k} {v}" for k, v in sorted(summary["status"].items()))
                  + f", stale {summary['stale']}")
        if summary["attested_computations"]:
            print(f"  attested computations: {summary['attested_computations']}")
        verdict = "NOT conformant" if errors else "conformant"
        print(f"  result:   {verdict}, {len(errors)} error(s), {len(warnings)} warning(s)")
    if errors or (args.strict and warnings):
        return 1
    return 0


# ---------------------------------------------------------------------------
# index
# ---------------------------------------------------------------------------

def read_existing_index(path: Path):
    """Return (frontmatter_text | None, {target: description}) from an existing index.md."""
    if not path.exists():
        return None, {}
    text = path.read_text(encoding="utf-8", errors="replace")
    fm_text, body, _, _ = split_frontmatter(text)
    descs: dict[str, str] = {}
    for line in body.split("\n"):
        m = INDEX_ENTRY_RE.match(line)
        if m:
            target = m.group(2).rstrip("/")
            if target.endswith("/index.md"):
                target = target[: -len("/index.md")]
            descs[target] = (m.group(3) or "").strip()
    return fm_text, descs


def existing_heading(path: Path) -> Optional[str]:
    """First `# Heading` of an existing index.md, so a files-only directory keeps its name."""
    if not path.exists():
        return None
    _, body, _, _ = split_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
    for line in body.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return None


def dir_has_md(d: Path) -> bool:
    return any(p.suffix == ".md" for p in d.rglob("*") if not any(x.startswith(".") for x in p.relative_to(d).parts))


def build_index(bundle: Path, d: Path) -> Optional[str]:
    fm_text, existing = read_existing_index(d / "index.md")
    is_root = d == bundle
    sections: list[tuple[str, list[tuple[str, str, str]]]] = []

    subdirs = [c for c in sorted(d.iterdir()) if c.is_dir() and not is_hidden(c, bundle) and dir_has_md(c)]
    if subdirs:
        entries = []
        for c in subdirs:
            desc = existing.get(c.name, "")
            if not desc:
                types: dict[str, int] = {}
                count = 0
                for p in sorted(c.glob("*.md")):
                    if p.name in RESERVED:
                        continue
                    count += 1
                    doc = Doc(bundle, p)
                    t = (doc.fm or {}).get("type") if doc.fm else None
                    if isinstance(t, str):
                        types[t] = types.get(t, 0) + 1
                if count:
                    desc = f"{count} concept{'s' if count != 1 else ''}"
                    if types:
                        desc += " (" + ", ".join(sorted(types)) + ")"
            entries.append((c.name, f"{c.name}/index.md", desc))
        sections.append(("Subdirectories", entries))

    groups: dict[str, list[tuple[str, str, str]]] = {}
    for p in sorted(d.glob("*.md")):
        if p.name in RESERVED or is_hidden(p, bundle):
            continue
        doc = Doc(bundle, p)
        fm = doc.fm or {}
        ctype = fm.get("type") if isinstance(fm.get("type"), str) and fm.get("type").strip() else "Untyped"
        title = fm.get("title") if isinstance(fm.get("title"), str) and fm.get("title").strip() else p.stem
        desc = fm.get("description") if isinstance(fm.get("description"), str) else ""
        desc = (desc or existing.get(p.name, "")).strip().replace("\n", " ")
        groups.setdefault(ctype, []).append((title, p.name, desc))
    for ctype in sorted(groups, key=str.lower):
        sections.append((ctype, sorted(groups[ctype], key=lambda e: e[0].lower())))

    others = [c for c in sorted(d.iterdir()) if c.is_file() and c.suffix != ".md" and not is_hidden(c, bundle)]
    if groups or subdirs:
        others = [c for c in others if c.name in existing]
    if others:
        heading = "Files"
        if not groups and not subdirs:
            heading = existing_heading(d / "index.md") or heading
        sections.append((heading, [(c.name, c.name, existing.get(c.name, "")) for c in others]))

    if not sections:
        return None

    out: list[str] = []
    if fm_text is not None:
        out += ["---", fm_text.strip("\n"), "---", ""]
    elif is_root:
        out += ["---", f'okf_version: "{OKF_VERSION}"', "---", ""]
    for heading, entries in sections:
        out.append(f"# {heading}")
        out.append("")
        for title, target, desc in entries:
            line = f"* [{title}]({target})"
            if desc:
                line += f" - {desc}"
            out.append(line)
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


def index_plan(bundle: Path) -> list[tuple[Path, Optional[str], str]]:
    """Return [(index_path, new_text, status)] where status is create|update|ok|skip."""
    plan = []
    dirs = {bundle}
    for p in iter_md(bundle):
        d = p.parent
        while d != bundle:
            dirs.add(d)
            d = d.parent
    for d in sorted(dirs):
        new = build_index(bundle, d)
        path = d / "index.md"
        if new is None:
            continue
        if not path.exists():
            plan.append((path, new, "create"))
            continue
        old = path.read_text(encoding="utf-8", errors="replace")
        norm_old = "\n".join(l.rstrip() for l in old.strip().split("\n"))
        norm_new = "\n".join(l.rstrip() for l in new.strip().split("\n"))
        plan.append((path, new, "ok" if norm_old == norm_new else "update"))
    return plan


def cmd_index(args) -> int:
    bundle = Path(args.bundle).resolve()
    if not bundle.is_dir():
        print(f"error: not a directory: {args.bundle}", file=sys.stderr)
        return 2
    plan = index_plan(bundle)
    changed = 0
    for path, new, status in plan:
        rel = path.relative_to(bundle).as_posix()
        if status == "ok":
            if not args.check:
                print(f"ok      {rel}")
            continue
        changed += 1
        if args.write:
            path.write_text(new, encoding="utf-8")
            print(f"{'created' if status == 'create' else 'updated'} {rel}")
        elif args.check:
            print(f"{'missing' if status == 'create' else 'stale'}   {rel}")
        else:
            old = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
            print(f"{status:7} {rel}")
            sys.stdout.writelines(difflib.unified_diff(
                old.splitlines(keepends=True), new.splitlines(keepends=True),
                fromfile=f"a/{rel}", tofile=f"b/{rel}",
            ))
            print()
    if args.check:
        print(f"{changed} index file(s) out of date" if changed else "all index files up to date")
        return 1 if changed else 0
    if not args.write and changed:
        print(f"{changed} index file(s) would change; re-run with --write to apply")
    elif args.write:
        print(f"{changed} index file(s) written")
    return 0


# ---------------------------------------------------------------------------
# log
# ---------------------------------------------------------------------------

def add_log_entry(path: Path, text: str, kind: str, date: str) -> str:
    bullet = f"* **{kind}**: {text.strip()}"
    if path.exists():
        content = path.read_text(encoding="utf-8", errors="replace")
    else:
        content = "# Update Log\n"
    fm_text, body, _, _ = split_frontmatter(content)
    prefix = f"---\n{fm_text.strip(chr(10))}\n---\n" if fm_text is not None else ""
    lines = body.split("\n")
    heading = f"## {date}"
    for i, line in enumerate(lines):
        if line.strip() == heading:
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            lines.insert(j, bullet)
            return prefix + "\n".join(lines).rstrip("\n") + "\n"
    block = [heading, bullet, ""]
    for i, line in enumerate(lines):
        if line.startswith("## "):
            lines[i:i] = block
            return prefix + "\n".join(lines).rstrip("\n") + "\n"
    if lines and lines[-1].strip():
        lines.append("")
    lines += block
    return prefix + "\n".join(lines).rstrip("\n") + "\n"


def cmd_log(args) -> int:
    bundle = Path(args.bundle).resolve()
    target_dir = (bundle / args.dir).resolve() if args.dir else bundle
    if not target_dir.is_dir():
        print(f"error: not a directory: {target_dir}", file=sys.stderr)
        return 2
    date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        print("error: --date must be YYYY-MM-DD", file=sys.stderr)
        return 2
    path = target_dir / "log.md"
    path.write_text(add_log_entry(path, args.text, args.kind, date), encoding="utf-8")
    print(f"logged under {date} in {path.relative_to(bundle).as_posix()}")
    return 0


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

SPEC_FRONTMATTER_SAMPLES = [
    # §4.3
    """type: BigQuery Table
title: Customer Orders
description: One row per completed customer order across all channels.
resource: https://console.cloud.google.com/bigquery?p=acme&d=sales&t=orders
tags: [sales, orders, revenue]
generated: { by: reference_agent/gemini-2.5-pro, at: 2026-05-28T14:30:00Z }
""",
    # §4.4 (quoted title containing a colon)
    """type: Playbook
title: "Incident response: data freshness alert"
description: Steps to triage a freshness alert on the orders pipeline.
tags: [oncall, incident]
generated: { by: human:ahormati, at: 2026-04-12T09:00:00Z }
""",
    # §5.1 + §5.2 block lists, bare verified mapping, usage_window
    """sources:
  - id: ga4-schema
    resource: https://developers.google.com/analytics/bigquery/export-schema
    title: GA4 BigQuery Export schema
    author: team:ga4-docs
    usage_count: 5000
    last_modified: 2026-05-30T00:00:00Z
usage_window: { from: 2026-06-01T00:00:00Z, to: 2026-06-30T00:00:00Z }
verified: { by: human:ahormati, at: 2026-06-25T09:00:00Z }
status: stable        # draft | stable | deprecated
stale_after: 2026-09-23T00:00:00Z   # content is stale on/after this instant
""",
    # §10.2 attested computation
    """type: Attested Computation
title: Revenue for fiscal year
runtime: bigquery
parameters:
  - { name: year, type: integer, required: true }
executor:
  resource: references/skills/run-on-bq.md
  receipt: [job_id, executed_sql, result]
attester:
  resource: references/attesters/revenue.py
verified:
  - { by: human:ahormati, at: 2026-06-25T09:00:00Z }
  - { by: process:finance-nightly, at: 2026-06-26T02:00:00Z }
not:
  - term: "revenue minus product cost only"
    why: "that is the pre-FY2026 definition (see gross-margin-legacy)."
    instead: "revenue minus full COGS"
""",
]


def _selftest_yaml():
    fm = parse_yaml(SPEC_FRONTMATTER_SAMPLES[0])
    assert fm["type"] == "BigQuery Table", fm
    assert fm["tags"] == ["sales", "orders", "revenue"], fm
    assert fm["generated"] == {"by": "reference_agent/gemini-2.5-pro", "at": "2026-05-28T14:30:00Z"}, fm
    assert fm["resource"].startswith("https://"), fm

    fm = parse_yaml(SPEC_FRONTMATTER_SAMPLES[1])
    assert fm["title"] == "Incident response: data freshness alert", fm

    fm = parse_yaml(SPEC_FRONTMATTER_SAMPLES[2])
    assert fm["sources"][0]["usage_count"] == 5000, fm
    assert fm["sources"][0]["author"] == "team:ga4-docs", fm
    assert fm["usage_window"]["to"] == "2026-06-30T00:00:00Z", fm
    assert fm["verified"] == {"by": "human:ahormati", "at": "2026-06-25T09:00:00Z"}, fm
    assert fm["status"] == "stable", fm
    assert fm["stale_after"] == "2026-09-23T00:00:00Z", fm

    fm = parse_yaml(SPEC_FRONTMATTER_SAMPLES[3])
    assert fm["parameters"] == [{"name": "year", "type": "integer", "required": True}], fm
    assert fm["executor"]["receipt"] == ["job_id", "executed_sql", "result"], fm
    assert len(fm["verified"]) == 2 and fm["verified"][1]["by"] == "process:finance-nightly", fm
    assert fm["not"][0]["instead"] == "revenue minus full COGS", fm

    assert parse_yaml('okf_version: "0.2"') == {"okf_version": "0.2"}
    assert parse_yaml("okf_version: 0.2")["okf_version"] == 0.2
    assert parse_yaml("a:\n- 1\n- two\n") == {"a": [1, "two"]}
    assert parse_yaml("desc: |\n  line one\n  line two\n")["desc"] == "line one\nline two\n"
    assert parse_yaml("t: 'it''s'")["t"] == "it's"
    assert parse_yaml("e:\nf: x") == {"e": None, "f": "x"}
    try:
        parse_yaml("a: [1, 2\n")
        raise AssertionError("expected YAMLError")
    except YAMLError:
        pass

    assert trust_tier({}) == "unverified"
    assert trust_tier({"verified": {"by": "process:x", "at": "2026-01-01T00:00:00Z"}}) == "machine-confirmed"
    assert trust_tier({"verified": [{"by": "process:x"}, {"by": "human:me"}]}) == "human-reviewed"
    assert parse_timestamp("2026-06-30T14:00:00Z") is not None
    assert parse_timestamp("2026-06-30T14:00:00+0530") is not None
    assert parse_timestamp("2026-06-30") is None
    assert parse_timestamp("2026-06-30T14:00:00") is None
    for good in ("reference_agent/gemini-2.5-pro", "human:ahormati", "process:finance-nightly", "team:ga4-docs"):
        assert ACTOR_RE.match(good), good
    for bad in ("ahormati", "some person", ""):
        assert not ACTOR_RE.match(bad), bad


def _write(root: Path, rel: str, text: str):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _selftest_bundle(tmp: Path):
    b = tmp / "bundle"
    _write(b, "index.md", '---\nokf_version: "0.2"\n---\n\n# Subdirectories\n\n* [metrics](metrics/index.md) - Metrics\n* [computations](computations/index.md) - Computations\n')
    _write(b, "log.md", "# Log\n\n## 2026-07-01\n* **Update**: something\n\n## not-a-date\n* **Creation**: bad heading\n\n## 2026-08-01\n* **Update**: out of order\n")
    _write(b, "metrics/index.md", "# Metric\n\n* [Revenue](revenue.md) - Recognized revenue.\n")
    _write(b, "metrics/revenue.md", """---
type: Metric
title: Revenue
description: Recognized revenue for a fiscal year.
tags: [finance]
status: stable
generated: { by: reference_agent/gemini-2.5-pro, at: 2026-06-20T22:53:05Z }
verified: { by: human:ahormati, at: 2026-06-25T09:00:00Z }
sources:
  - id: rev-policy
    resource: https://wiki.acme/finance/revenue-recognition
    title: Revenue recognition policy
---

# Definition

Computed by [the revenue computation](/computations/revenue.md), per policy.[^rev-policy]
Also see [customers](/tables/customers.md) which does not exist yet, and an
unknown footnote.[^nope]

[^rev-policy]: Revenue recognition policy
""")
    _write(b, "metrics/legacy.md", """---
type: Metric
title: Legacy
timestamp: '2026-05-28T22:53:05+00:00'
---

# Citations
- https://wiki.acme/finance/fpa-handbook
""")
    _write(b, "computations/revenue.md", """---
type: Attested Computation
title: Revenue for fiscal year
description: Recognized revenue for a fiscal year.
runtime: bigquery
parameters:
  - { name: year, type: integer, required: true }
executor:
  resource: /references/skills/run-on-bq.md
  receipt: [job_id, executed_sql, result]
attester:
  resource: /references/attesters/missing.py
generated: { by: reference_agent/gemini-2.5-pro, at: 2026-06-28T14:00:00Z }
verified: { by: process:finance-nightly, at: 2026-06-12T08:00:00Z }
stale_after: 2026-06-15T00:00:00Z
---

# Computation

```sql
SELECT SUM(amount) AS revenue FROM finance.recognized_revenue WHERE fiscal_year = @year
```
""")
    _write(b, "computations/noruntime.md", "---\ntype: Attested Computation\ntitle: Broken\ndescription: Missing runtime and computation.\n---\n\nNothing here.\n")
    _write(b, "references/skills/run-on-bq.md", "---\ntype: Skill\ntitle: Run on BigQuery\ndescription: Executor.\ngenerated: { by: human:kliu, at: 2026-06-30T14:00:00Z }\n---\n\n# Steps\n\n1. Run it.\n")
    _write(b, "bad/nofm.md", "# Just markdown\n\nNo frontmatter here.\n")
    _write(b, "bad/notype.md", "---\ntitle: Untyped\ndescription: Has frontmatter but no type.\n---\n\nBody.\n")
    _write(b, "bad/badyaml.md", "---\ntype: [unterminated\n---\n\nBody.\n")
    _write(b, "bad/index.md", "---\ntype: Index\n---\n\n# Bad\n\n* [nofm](nofm.md) - no frontmatter\n* [gone](gone.md) - missing target\n")
    _write(b, "bad/status.md", "---\ntype: Note\ndescription: Weird status and actor.\nstatus: archived\ngenerated: { by: somebody, at: 2026-06-30 }\nverified:\n  - by: human:x\n---\n\nBody.\n")
    return b


def selftest() -> int:
    _selftest_yaml()
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        b = _selftest_bundle(tmp)
        now = parse_timestamp("2026-07-01T00:00:00Z")
        assert now is not None
        findings, summary = validate_bundle(b, now)
        codes = {(f.path, f.code) for f in findings}

        def has(path, code):
            assert (path, code) in codes, f"expected {code} on {path}; got {sorted(codes)}"

        def lacks(path, code):
            assert (path, code) not in codes, f"unexpected {code} on {path}"

        has("bad/nofm.md", "E001")
        has("bad/badyaml.md", "E002")
        has("bad/notype.md", "E003")
        has("bad/index.md", "E004")
        has("bad/index.md", "W114")
        has("log.md", "E005")
        has("log.md", "W121")
        has("computations/noruntime.md", "E006")
        has("computations/noruntime.md", "W112")
        has("computations/revenue.md", "W106")
        has("computations/revenue.md", "W111")
        lacks("computations/revenue.md", "W112")
        has("metrics/revenue.md", "W110")
        has("metrics/revenue.md", "W108")
        lacks("metrics/revenue.md", "W101")
        has("metrics/legacy.md", "W118")
        has("metrics/legacy.md", "W101")
        has("metrics/index.md", "W115")
        has("bad/status.md", "W105")
        has("bad/status.md", "W103")
        has("bad/status.md", "W102")
        has("bad/status.md", "W116")
        has("computations/index.md", "W120")
        has("references/skills/index.md", "W120")
        assert summary["okf_version"] == "0.2", summary
        assert summary["trust"] == {"human-reviewed": 2, "machine-confirmed": 1, "unverified": 4}, summary["trust"]
        assert summary["stale"] == 1, summary
        assert summary["attested_computations"] == 2, summary
        # footnote with a matching id is not flagged
        assert not any(f.code == "W108" and "rev-policy" in f.message for f in findings)

        # index generation
        plan = index_plan(b)
        statuses = {p.relative_to(b).as_posix(): s for p, _, s in plan}
        assert statuses["computations/index.md"] == "create", statuses
        assert statuses["metrics/index.md"] == "update", statuses
        assert statuses["index.md"] == "update", statuses
        for path, new, status in plan:
            if status != "ok":
                path.write_text(new, encoding="utf-8")
        root_index = (b / "index.md").read_text()
        assert root_index.startswith('---\nokf_version: "0.2"\n---\n'), root_index
        assert "* [metrics](metrics/index.md) - Metrics" in root_index, root_index
        assert "* [references](references/index.md)" in root_index, root_index
        comp_index = (b / "computations/index.md").read_text()
        assert comp_index.startswith("# Attested Computation\n\n* [Broken](noruntime.md) - Missing runtime and computation.\n* [Revenue for fiscal year](revenue.md)"), comp_index
        assert "# Subdirectories\n\n* [skills](skills/index.md) - 1 concept (Skill)" in (b / "references/index.md").read_text()
        findings2, _ = validate_bundle(b, now)
        codes2 = {f.code for f in findings2}
        assert "W115" not in codes2 and "W120" not in codes2, sorted(codes2)
        plan2 = index_plan(b)
        assert all(s == "ok" for _, _, s in plan2), [(p.name, s) for p, _, s in plan2]

        # log
        log = b / "log.md"
        log.write_text("---\ntype: Log\n---\n# Log\n\n## 2026-07-01\n* **Update**: first\n")
        log.write_text(add_log_entry(log, "same day", "Creation", "2026-07-01"))
        log.write_text(add_log_entry(log, "newer day", "Update", "2026-07-02"))
        text = log.read_text()
        assert text.startswith("---\ntype: Log\n---\n# Log\n\n## 2026-07-02\n* **Update**: newer day\n\n## 2026-07-01\n* **Creation**: same day\n* **Update**: first\n"), text
        fresh = tmp / "fresh.md"
        fresh.write_text(add_log_entry(fresh, "born", "Initialization", "2026-01-01"))
        assert fresh.read_text() == "# Update Log\n\n## 2026-01-01\n* **Initialization**: born\n", fresh.read_text()
        findings3, _ = validate_bundle(b, now)
        assert not any(f.path == "log.md" for f in findings3), [str(f) for f in findings3 if f.path == "log.md"]
    print("selftest ok")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        try:
            return selftest()
        except AssertionError as exc:
            print(f"selftest FAILED: {exc}", file=sys.stderr)
            return 1
    parser = argparse.ArgumentParser(prog="okf.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"okf.py {__version__} (OKF {OKF_VERSION})")
    sub = parser.add_subparsers(dest="cmd")

    v = sub.add_parser("validate", help="check a bundle for OKF v0.2 conformance and lint issues")
    v.add_argument("bundle")
    v.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    v.add_argument("--json", action="store_true", help="machine-readable output")
    v.add_argument("--now", help="pin 'now' (ISO 8601 with offset) for staleness checks")
    v.set_defaults(func=cmd_validate)

    ix = sub.add_parser("index", help="regenerate index.md files from frontmatter")
    ix.add_argument("bundle")
    g = ix.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true", help="write the files (default is a dry run with diffs)")
    g.add_argument("--check", action="store_true", help="exit 1 if any index.md is missing or stale")
    ix.set_defaults(func=cmd_index)

    lg = sub.add_parser("log", help="prepend a dated entry to log.md")
    lg.add_argument("bundle")
    lg.add_argument("text")
    lg.add_argument("--kind", default="Update", help="bold lead word: Update, Creation, Deprecation, Initialization, ...")
    lg.add_argument("--date", help="YYYY-MM-DD (default: today, UTC)")
    lg.add_argument("--dir", help="subdirectory whose log.md to write (default: bundle root)")
    lg.set_defaults(func=cmd_log)

    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
