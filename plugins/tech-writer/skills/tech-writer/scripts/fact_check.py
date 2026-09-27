#!/usr/bin/env python3
"""Report facts that a documentation rewrite may have lost.

The tech-writer skill rewrites prose for clarity and length. Concision passes
are where facts leak: a qualifier reads as filler, a reason reads as padding,
a duplicate turns out to carry one extra condition. This script compares the
original file with the rewrite and lists what went missing, so the writer can
restore it or justify the removal in the report.

It checks two things:

  * Literals -- tokens that must survive verbatim: fenced code blocks, inline
    code spans, URLs and link targets, quoted strings, and any token that holds
    a digit, a path separator, an underscore, a leading dash, or two or more
    capitals (numbers, versions, dates, identifiers, flags, paths, acronyms,
    environment variables). A literal counts as lost when the rewrite holds
    fewer copies of it than the original.
  * Qualifiers -- words that carry meaning even though they look like padding:
    negations, conditions, limits and quantifiers, obligation and possibility,
    and cause or purpose. Rewording legitimately swaps one word for another in
    the same class ("because" -> "since"), so the script compares class totals
    in prose and flags a class whose total drops.

A finding is a prompt to look, not a verdict. Expanding an abbreviation (STE
rule 2.x) or replacing "etc." removes a literal on purpose; say so in the
report. A clean result does not prove the rewrite kept every fact either:
reasons, consequences, and examples can vanish without touching a literal or
a qualifier, so the writer still re-reads the original paragraph by paragraph.

Usage
-----
    python3 fact_check.py ORIGINAL REWRITE    compare two files
    python3 fact_check.py --json ORIGINAL REWRITE
    python3 fact_check.py --selftest

Snapshot the file before you edit it, then pass the snapshot as ORIGINAL.

Exit codes: 0 nothing lost, 1 findings present (or --selftest failure), 2 usage
or IO error. Stdlib only, Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

VERSION = "1.0.0"

FENCE_RE = re.compile(r"^([ \t]*)(`{3,}|~{3,})[^\n]*\n.*?^\1\2[ \t]*$", re.M | re.S)
INLINE_CODE_RE = re.compile(r"(`+)(.+?)\1", re.S)
LINK_TARGET_RE = re.compile(r"\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)|^\s*\[[^\]]+\]:\s*(\S+)", re.M)
URL_RE = re.compile(r"\b(?:https?|ftp|ssh|file)://[^\s<>()\[\]`\"']+|\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
QUOTE_RE = re.compile(r"\"([^\"\n]{1,200})\"|“([^”\n]{1,200})”")
WORD_RE = re.compile(r"-{1,2}\w[\w.=-]*|[~$%@#/\w][\w./:%@#+~=-]*")
TRAILING = ".,;:!?)]}'\""

QUALIFIERS: dict[str, list[str]] = {
    "negation": [
        "not", "no", "never", "none", "nothing", "neither", "nor", "cannot",
        "without", "n't",
    ],
    "condition": [
        "if", "unless", "until", "when", "whenever", "while", "before",
        "after", "otherwise", "provided", "only if", "as long as",
    ],
    "limit": [
        "only", "all", "every", "each", "always", "except", "exactly",
        "at least", "at most", "maximum", "minimum", "up to", "no more than",
        "no fewer than", "per", "usually", "often", "sometimes", "rarely",
        "typically", "most", "some", "under", "over", "less than",
        "more than", "fewer than", "within", "approximately", "roughly",
    ],
    "obligation": [
        "must", "shall", "should", "required", "requires", "require",
        "mandatory", "optional", "may", "might", "can", "could",
    ],
    "cause": [
        "because", "since", "so that", "therefore", "thus", "hence",
        "as a result", "due to", "in order to", "to avoid", "to prevent",
        "which means", "reason", "why",
    ],
}


def split_code(text: str) -> tuple[list[str], str]:
    """Return the fenced code blocks and the text with them blanked out."""
    blocks = [m.group(0).strip() for m in FENCE_RE.finditer(text)]
    return blocks, FENCE_RE.sub("\n", text)


def is_literal(token: str) -> bool:
    if len(token) < 2 and not token.isdigit():
        return False
    return bool(
        re.search(r"\d", token)
        or "/" in token
        or "_" in token
        or token.startswith("-")
        or token.startswith("$")
        or re.search(r"[A-Z].*[A-Z]", token)
        or re.search(r"\w\.\w", token)
    )


def literals(text: str) -> Counter:
    found: Counter = Counter()
    blocks, prose = split_code(text)
    for block in blocks:
        first = block.splitlines()[0][:60]
        found[f"code block: {first}"] += 1
    for m in INLINE_CODE_RE.finditer(prose):
        found[f"`{m.group(2).strip()}`"] += 1
    prose = INLINE_CODE_RE.sub(" ", prose)
    for m in LINK_TARGET_RE.finditer(prose):
        found[f"link: {m.group(1) or m.group(2)}"] += 1
    prose = LINK_TARGET_RE.sub(" ", prose)
    for m in URL_RE.finditer(prose):
        found[m.group(0).rstrip(TRAILING)] += 1
    prose = URL_RE.sub(" ", prose)
    for m in QUOTE_RE.finditer(prose):
        found[f"\"{m.group(1) or m.group(2)}\""] += 1
    for m in WORD_RE.finditer(prose):
        token = m.group(0).rstrip(TRAILING)
        if is_literal(token):
            found[token] += 1
    return found


def prose_only(text: str) -> str:
    _, prose = split_code(text)
    prose = INLINE_CODE_RE.sub(" ", prose)
    prose = URL_RE.sub(" ", prose)
    return prose.replace("’", "'").lower()


def qualifier_counts(text: str) -> dict[str, int]:
    prose = prose_only(text)
    counts = {}
    for name, words in QUALIFIERS.items():
        total = 0
        for word in words:
            if word == "n't":
                total += len(re.findall(r"\w+n't\b", prose))
            else:
                total += len(re.findall(r"\b" + re.escape(word) + r"\b", prose))
        counts[name] = total
    return counts


def compare(original: str, rewrite: str) -> dict:
    before, after = literals(original), literals(rewrite)
    lost = {
        token: {"before": n, "after": after.get(token, 0)}
        for token, n in before.items()
        if after.get(token, 0) < n
    }
    q_before, q_after = qualifier_counts(original), qualifier_counts(rewrite)
    dropped = {
        name: {"before": q_before[name], "after": q_after[name]}
        for name in QUALIFIERS
        if q_after[name] < q_before[name]
    }
    return {"literals_lost": lost, "qualifiers_dropped": dropped}


def render(result: dict, original: str, rewrite: str) -> str:
    lines = []
    if result["literals_lost"]:
        lines.append("-- literals missing from the rewrite (restore, or justify in the report) --")
        for token, n in result["literals_lost"].items():
            lines.append(f"  {token}  (original {n['before']}, rewrite {n['after']})")
    if result["qualifiers_dropped"]:
        lines.append("-- qualifier classes that dropped (re-read the matching sentences) --")
        for name, n in result["qualifiers_dropped"].items():
            words = ", ".join(QUALIFIERS[name][:8])
            lines.append(f"  {name}: {n['before']} -> {n['after']}  ({words}, ...)")
    if not lines:
        lines.append(f"{rewrite}: no literals lost, no qualifier class dropped (compared with {original})")
    return "\n".join(lines)


def selftest() -> int:
    cases = [
        # A concision pass that drops a number, a flag, and a condition.
        (
            "If the build fails, run `make clean` and retry up to 3 times with --verbose.",
            "Run `make clean` and retry.",
            {"3", "--verbose"},
            {"condition", "limit"},
        ),
        # A reword that keeps every fact is clean.
        (
            "The token is not valid after 60 minutes because the issuer rotates keys.",
            "The token expires after 60 minutes. It is not valid then, because the issuer rotates keys.",
            set(),
            set(),
        ),
        # Contractions count as negations, so expanding one is not a loss.
        ("Don't delete PROD_DB.", "Do not delete PROD_DB.", set(), set()),
        # Code blocks and link targets must survive verbatim.
        (
            "See [the guide](docs/a.md).\n\n```bash\nrm -rf build/\n```\n",
            "See the guide.\n",
            {"link: docs/a.md", "code block: ```bash"},
            set(),
        ),
    ]
    failed = 0
    for i, (orig, new, want_lit, want_q) in enumerate(cases, 1):
        res = compare(orig, new)
        got_lit = set(res["literals_lost"])
        got_q = set(res["qualifiers_dropped"])
        if not want_lit <= got_lit or (not want_lit and got_lit) or got_q != want_q:
            failed += 1
            print(f"selftest case {i} FAILED: literals {sorted(got_lit)}, qualifiers {sorted(got_q)}")
    print(f"selftest: {len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Report facts a documentation rewrite may have lost.")
    ap.add_argument("original", nargs="?", help="snapshot of the file before the rewrite")
    ap.add_argument("rewrite", nargs="?", help="the rewritten file")
    ap.add_argument("--json", action="store_true", help="print the findings as JSON")
    ap.add_argument("--selftest", action="store_true", help="run the built-in assertions")
    ap.add_argument("--version", action="version", version=VERSION)
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not args.original or not args.rewrite:
        ap.error("ORIGINAL and REWRITE are required")
    try:
        original = Path(args.original).read_text(encoding="utf-8")
        rewrite = Path(args.rewrite).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"fact_check: {exc}", file=sys.stderr)
        return 2
    result = compare(original, rewrite)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render(result, args.original, args.rewrite))
    return 1 if result["literals_lost"] or result["qualifiers_dropped"] else 0


if __name__ == "__main__":
    sys.exit(main())
