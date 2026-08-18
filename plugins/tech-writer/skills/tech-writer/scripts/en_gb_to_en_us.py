#!/usr/bin/env python3
"""Convert British English spellings to American English in Markdown documents.

Both standards the tech-writer skill applies -- Google's Technical Writing
guidelines and ASD-STE100 Simplified Technical English -- ask for US spelling,
so this script is the mechanical half of that pass. It is stdlib only, single
file, Python 3.9+, and safe to run from any repository.

Usage
-----
    python3 en_gb_to_en_us.py --check  FILE...   report findings, never writes
    python3 en_gb_to_en_us.py --diff   FILE...   unified diff on stdout
    python3 en_gb_to_en_us.py --write  FILE...   rewrite in place, print a summary
    python3 en_gb_to_en_us.py --stdin            filter stdin to stdout
    python3 en_gb_to_en_us.py --selftest         run the built-in assertions

Modifiers: --json (machine-readable output for --check, --diff and --write),
--stats (counters; on stderr under --stdin so stdout stays the document),
--aggressive (also apply the ambiguous tier), --no-rule NAME (disable a rule
family or a tier, may be repeated), -q/--quiet (no stdout at all), --version.
FILE arguments are plain file paths -- directories are an error, and no
globbing is performed. Every path is read before anything is scanned or
written, so one bad path never discards findings or half-rewrites a tree.

Findings look like::

    docs/guide.md:12:5: colour -> color  (rule: our-or)
    docs/guide.md:31:9: analyses -> analyzes  (rule: ambiguous; verb or plural)

The column is the 1-based character offset of the original token (characters,
not bytes, which is what an editor shows), so it stays valid no matter how the
replacement length differs. The name after `rule:` is exactly what --no-rule
accepts, `ambiguous` and `proper-noun` included.

Exit codes: 0 clean, 1 findings present (--check and --selftest failure), 2
usage or IO error.

Safety model
------------
Nothing outside prose is ever rewritten. The document is first split into
protected regions and prose:

  * fenced code (``` and ~~~, any info string), indented code, inline code spans
  * HTML tags and attributes, and the whole body of the raw-text and inline
    literal elements: pre, code, samp, kbd, var, tt, script, style, svg, ...
  * autolinks, bare URLs, email addresses, HTML entities
  * link and image destinations, reference definitions, reference usages, and
    shortcut references (`[colour]` when `[colour]:` is defined -- the visible
    word is the link target there, so rewriting it unresolves the link)
  * template expressions: {{mustache}}, {% statement %}, ${shell}, %(printf)s
    and {format_field}
  * identifier-shaped tokens: snake_case, camelCase, --flags, paths, file names,
    semver, hashes
  * any token holding a non-ASCII letter, which is not an English word

One thing the masking layer cannot see is a document that spells both forms on
purpose: a `| colour | color |` conversion table flattens into two American
columns. Wrap such a table in `<!-- engb:off -->`.

Then a per-token guard rejects anything that still looks like an identifier: a
case pattern other than lower/Title/UPPER, a neighbouring connector character,
or a hyphen run that is not clean prose hyphenation. `--colour-output` and
`ColourMap` therefore survive, while `behaviour-driven` converts.

YAML frontmatter is treated asymmetrically on purpose. Keys are never touched,
and a value converts only under an allow-listed prose key (`description`,
`title`, `summary`, ...). Frontmatter is prose and machine data at the same
time -- a `description` renders to readers, a `name` is a lookup key -- so a
converter that treated it uniformly would be wrong in one direction. Denying
every unrecognised key fails safe: the worst outcome is a missed conversion in
a prose field, never a broken identifier.

Escape hatches, written as HTML comments (`engb:` and `gb2us:` are synonyms)::

    <!-- engb:off -->  ... <!-- engb:on -->   skip the enclosed span
    <!-- engb:ignore-line -->                 skip the line it appears on
    <!-- engb:ignore-next -->                 skip the next non-blank line
    <!-- engb:skip-file -->                   skip the file (first 20 lines)

Two tiers of finding
--------------------
Certain findings are applied by --write. Ambiguous ones (`analyses`, `disc`,
`dialogue`, `spelt`, `calibre`, ...) and proper-noun demotions (`Earl Grey`,
`Erasmus Programme`) are reported but never applied, because a machine cannot
tell the two readings apart. --aggressive promotes the ambiguous tier only;
proper-noun demotions are never written under any flag.
"""

from __future__ import annotations

import argparse
import bisect
import contextlib
import difflib
import io
import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2

PROGRAM = "en_gb_to_en_us.py"
VERSION = "1.1.0"


# ==========================================================================
# Part 1 -- masking layer
#
# Split the document into protected regions and prose. The invariants:
#   1. restore(*protect(t)) == t for every input.
#   2. A placeholder is U+E000 + decimal digits + U+E001. It holds no ASCII
#      letters, so no spelling rule can rewrite any part of it.
#   3. Sentinels cannot collide with document content: a sentinel already in
#      the source is captured as a region at the highest precedence.
#   4. No region contains a newline, so the masked text has the same lines, in
#      the same order, as the source, and line numbers stay usable.
# ==========================================================================

MASK_OPEN = "\ue000"
MASK_CLOSE = "\ue001"
_SENTINELS = (MASK_OPEN, MASK_CLOSE)
_PLACEHOLDER_RE = re.compile(MASK_OPEN + r"(\d+)" + MASK_CLOSE)

# Frontmatter keys whose scalar is natural-language prose. Everything else in
# frontmatter is an identifier, a UI literal, or a tool list, and is protected.
PROSE_FRONTMATTER_KEYS = frozenset(
    {
        "description",
        "short_description",
        "shortdescription",
        "long_description",
        "summary",
        "excerpt",
        "abstract",
        "caption",
        "display_name",
        "displayname",
        "blurb",
        "tagline",
        "title",
        "subtitle",
        "note",
    }
)

# Elements whose content is not Markdown and not prose. The inline literal
# elements matter as much as the block ones: `<code>colour</code>` names a
# configuration key, and rewriting it breaks the thing it documents.
RAW_TEXT_ELEMENTS = (
    "script",
    "style",
    "pre",
    "textarea",
    "svg",
    "math",
    "template",
    "code",
    "samp",
    "kbd",
    "var",
    "tt",
)

# Region kinds that are identifier-shaped tokens. Only these get glued to
# adjacent word characters (see _expand_identifier_regions).
_GLUE_KINDS = frozenset(
    {
        "camel_case",
        "email",
        "env_var",
        "file_ext",
        "flag",
        "hex",
        "path",
        "semver",
        "snake_case",
        "template_var",
    }
)

_FILE_EXTENSIONS = (
    "md|markdown|mdx|py|pyi|json|jsonc|ya?ml|toml|ini|cfg|conf|env|lock|txt|log|"
    "html?|css|scss|js|jsx|mjs|cjs|tsx?|sh|bash|zsh|fish|ps1|rb|go|rs|java|kt|"
    "c|h|cc|cpp|hpp|cs|php|pl|sql|swift|zip|tar|gz|tgz|pdf|png|jpe?g|gif|webp|"
    "svg|ico|mp4|mov|webm|csv|tsv|xml|patch|diff|gitignore|gitattributes"
)


@dataclass(frozen=True)
class Region:
    """A half-open [start, end) slice of the source that must not be rewritten."""

    kind: str
    start: int
    end: int

    def text(self, source: str) -> str:
        return source[self.start : self.end]


@dataclass(frozen=True)
class _Line:
    start: int
    end: int  # end of the content, never includes the newline
    text: str


def _split_lines(text: str) -> list[_Line]:
    """Every line as (start offset, end offset, content without the newline)."""
    lines = []
    pos = 0
    for raw in text.splitlines(keepends=True):
        content = raw.rstrip("\n").rstrip("\r")
        lines.append(_Line(pos, pos + len(content), content))
        pos += len(raw)
    return lines


def _indent_width(line: str) -> int:
    """Indent in columns, tabs expanded to the next 4-column stop."""
    width = 0
    for ch in line:
        if ch == " ":
            width += 1
        elif ch == "\t":
            width += 4 - (width % 4)
        else:
            break
    return width


_QUOTE_PREFIX_RE = re.compile(r"^(?:[ \t]{0,3}>[ \t]?)+")


def _strip_quote(line: str) -> tuple[str, int]:
    """Strip block quote markers. Returns (body, characters consumed)."""
    m = _QUOTE_PREFIX_RE.match(line)
    if not m:
        return line, 0
    return line[m.end() :], m.end()


def line_col(text: str, offset: int) -> tuple[int, int]:
    """1-based (line, column) of a source offset, for findings output."""
    line = text.count("\n", 0, offset) + 1
    bol = text.rfind("\n", 0, offset) + 1
    return line, offset - bol + 1


def _scan_sentinels(text: str, out: list[Region]) -> None:
    """Pass 0: a sentinel already in the source becomes its own region."""
    for i, ch in enumerate(text):
        if ch in _SENTINELS:
            out.append(Region("sentinel", i, i + 1))


# `engb:` is this script's own prefix; `gb2us:` is accepted as a synonym so a
# document written for either spelling of the directive keeps working.
# The prefix is optional on `verbatim` and the separator inside a two-word
# directive is free, so `engb:verbatim` and `engb:ignoreline` -- the two most
# likely guesses -- do what the writer meant instead of nothing at all.
_ENGB = r"(?:engb|gb2us)\s*:\s*"
_DIRECTIVE_OFF_RE = re.compile(
    r"<!--\s*(?:%soff|(?:%s)?verbatim)\s*-->" % (_ENGB, _ENGB), re.IGNORECASE
)
_DIRECTIVE_ON_RE = re.compile(
    r"<!--\s*(?:%son|(?:%s)?end[-_ ]?verbatim)\s*-->" % (_ENGB, _ENGB), re.IGNORECASE
)
_DIRECTIVE_LINE_RE = re.compile(
    r"<!--\s*%signore[-_ ]?line\s*-->" % _ENGB, re.IGNORECASE
)
_DIRECTIVE_NEXT_RE = re.compile(
    r"<!--\s*%signore[-_ ]?next\s*-->" % _ENGB, re.IGNORECASE
)
SKIP_FILE_RE = re.compile(r"<!--\s*%sskip[-_ ]?file\s*-->" % _ENGB, re.IGNORECASE)

# A directive nobody recognises is worse than no directive: the writer thinks
# the text is protected and it is not. Every `engb:` comment is checked.
_ANY_DIRECTIVE_RE = re.compile(r"<!--\s*%s([A-Za-z][\w -]*?)\s*-->" % _ENGB, re.IGNORECASE)
_DIRECTIVE_SEP_RE = re.compile(r"[-_ ]+")
KNOWN_DIRECTIVES = frozenset(
    {"off", "on", "verbatim", "endverbatim", "ignoreline", "ignorenext", "skipfile"}
)


def directive_warnings(text: str, path: str) -> list:
    """Every `engb:` comment whose name is not a directive this script knows."""
    warnings = []
    for number, line in enumerate(text.splitlines(), 1):
        for match in _ANY_DIRECTIVE_RE.finditer(line):
            name = _DIRECTIVE_SEP_RE.sub("", match.group(1)).lower()
            if name not in KNOWN_DIRECTIVES:
                warnings.append(
                    "%s:%d: unknown directive %r, text is NOT protected "
                    "(known: off, on, ignore-line, ignore-next, skip-file, verbatim)"
                    % (path, number, match.group(1))
                )
    return warnings


def _scan_directives(text: str, out: list[Region]) -> None:
    """Pass 1: protect `<!-- engb:off -->` .. `<!-- engb:on -->` spans.

    `<!-- verbatim -->` is the same opener; with no explicit closer it covers
    only the next blank-line-delimited block, which is how a quoted transcript
    gets excluded without wrapping it in a fence.
    """
    pos = 0
    while True:
        opener = _DIRECTIVE_OFF_RE.search(text, pos)
        if opener is None:
            break
        one_block = "verbatim" in opener.group(0).lower()
        closer = _DIRECTIVE_ON_RE.search(text, opener.end())
        if one_block:
            limit = _end_of_next_block(text, opener.end())
            if closer is not None and closer.start() < limit:
                end = closer.end()
            else:
                end = limit
        else:
            end = closer.end() if closer is not None else len(text)
        out.append(Region("directive", opener.start(), end))
        pos = end
    _scan_ignore_directives(text, out)


def _scan_ignore_directives(text: str, out: list[Region]) -> None:
    """Protect the line an `ignore-line` sits on, or the line after `ignore-next`."""
    lines = _split_lines(text)
    for i, ln in enumerate(lines):
        if _DIRECTIVE_LINE_RE.search(ln.text):
            out.append(Region("directive", ln.start, ln.end))
        if _DIRECTIVE_NEXT_RE.search(ln.text):
            for j in range(i + 1, len(lines)):
                if lines[j].text.strip():
                    out.append(Region("directive", lines[j].start, lines[j].end))
                    break


def _end_of_next_block(text: str, pos: int) -> int:
    """End offset of the first non-blank block after the line holding pos."""
    lines = _split_lines(text)
    starts = [ln.start for ln in lines]
    i = max(bisect.bisect_right(starts, pos) - 1, 0) + 1
    while i < len(lines) and not lines[i].text.strip():
        i += 1
    end = pos
    while i < len(lines) and lines[i].text.strip():
        end = lines[i].end
        i += 1
    return max(end, pos)


_FM_KEY_RE = re.compile(r"^(?P<lead>[ \t]*)(?P<key>[A-Za-z_][\w.-]*)(?P<sep>[ \t]*:[ \t]*)")
_FM_BLOCK_SCALAR_RE = re.compile(r"^[|>][+-]?\d*$")


def _scan_frontmatter(lines: list[_Line], out: list[Region]) -> int:
    """Pass 2: protect frontmatter keys and non-prose values. Returns the first
    body line index."""
    if not lines or lines[0].text.strip() != "---":
        return 0
    close = None
    for i in range(1, len(lines)):
        if lines[i].text.strip() in ("---", "..."):
            close = i
            break
    if close is None:
        return 0
    # A leading `---` is only frontmatter if what follows looks like YAML;
    # otherwise it is a thematic break and the text below it is prose.
    first = next((lines[i].text for i in range(1, close) if lines[i].text.strip()), "")
    if not (_FM_KEY_RE.match(first) or _LIST_RE.match(first)):
        return 0

    out.append(Region("frontmatter", lines[0].start, lines[0].end))
    out.append(Region("frontmatter", lines[close].start, lines[close].end))

    prose_block_indent = None  # set while inside a prose block scalar
    for i in range(1, close):
        ln = lines[i]
        if not ln.text.strip():
            continue
        indent = _indent_width(ln.text)
        if prose_block_indent is not None:
            if indent > prose_block_indent:
                continue  # prose continuation line, leave unprotected
            prose_block_indent = None
        m = _FM_KEY_RE.match(ln.text)
        if m is None:
            out.append(Region("frontmatter", ln.start, ln.end))
            continue
        key_end = ln.start + m.end()
        out.append(Region("frontmatter", ln.start, key_end))
        value = ln.text[m.end() :]
        if m.group("key").lower() not in PROSE_FRONTMATTER_KEYS:
            if value:
                out.append(Region("frontmatter", key_end, ln.end))
            continue
        if _FM_BLOCK_SCALAR_RE.match(value.strip()):
            out.append(Region("frontmatter", key_end, ln.end))
            prose_block_indent = _indent_width(ln.text)
        # else: a prose scalar, left for the inline passes
    return close + 1


_FENCE_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})(?P<info>.*)$")
_LIST_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<marker>[-*+]|\d{1,9}[.)])(?P<space>[ \t]+|$)")
_REFDEF_RE = re.compile(
    r"""^[ \t]{0,3}(?P<label>\[[^\]\n]+\]:)[ \t]*
        (?P<dest><[^<>\n]*>|[^\s<>]+)
        (?P<title>[ \t]+(?P<quote>["'(])(?P<inner>[^\n]*)(?P<endq>["')]))?[ \t]*$""",
    re.VERBOSE,
)


def _valid_fence(body: str) -> "re.Match | None":
    """Match a code fence opener. A backtick fence cannot carry a backtick info string."""
    fence = _FENCE_RE.match(body)
    if fence is None:
        return None
    if fence.group("fence")[0] == "`" and "`" in fence.group("info"):
        return None
    return fence


def _add_line_regions(
    lines: list[_Line], first: int, last: int, kind: str, out: list[Region]
) -> None:
    for i in range(first, last + 1):
        ln = lines[i]
        if ln.end > ln.start:
            out.append(Region(kind, ln.start, ln.end))


def _consume_fence(
    lines: list[_Line], i: int, marker: str, opener_indent: int, out: list[Region]
) -> int:
    """Protect a fenced code block. Returns the next line index to inspect."""
    char = marker[0]
    length = len(marker)
    closer = re.compile(r"^[ \t]*" + re.escape(char) + "{%d,}[ \t]*$" % length)
    last = len(lines) - 1  # an unclosed fence runs to the end of the document
    for j in range(i + 1, len(lines)):
        body, _ = _strip_quote(lines[j].text)
        if closer.match(body) and _indent_width(body) <= opener_indent + 3:
            last = j
            break
    _add_line_regions(lines, i, last, "fenced_code", out)
    return last + 1


def _consume_indented_code(lines: list[_Line], i: int, container: int, out: list[Region]) -> int:
    """Protect a run of indented code lines. Returns the next line index."""
    last = i
    j = i
    while j < len(lines):
        body, _ = _strip_quote(lines[j].text)
        if not body.strip():
            j += 1
            continue
        if _indent_width(body) >= container + 4:
            last = j
            j += 1
            continue
        break
    _add_line_regions(lines, i, last, "indented_code", out)
    return last + 1


def _scan_blocks(text: str, out: list[Region]) -> None:
    """Pass 3: block structure -- fences, indented code, reference definitions.

    A list-item content-indent stack disambiguates genuine indented code from a
    four-space list continuation paragraph, which is prose.
    """
    lines = _split_lines(text)
    i = _scan_frontmatter(lines, out)
    stack: list[int] = []  # content indent of each open list item
    prev_blank = True
    while i < len(lines):
        ln = lines[i]
        body, qoff = _strip_quote(ln.text)
        if not body.strip():
            prev_blank = True
            i += 1
            continue
        indent = _indent_width(body)
        # A blank line then a dedent closes list items; without the blank line
        # the dedented line is a lazy paragraph continuation.
        while stack and prev_blank and indent < stack[-1]:
            stack.pop()
        container = stack[-1] if stack else 0

        fence = _valid_fence(body)
        if fence is not None and indent < container + 4:
            i = _consume_fence(lines, i, fence.group("fence"), indent, out)
            prev_blank = False
            continue
        if prev_blank and indent >= container + 4:
            i = _consume_indented_code(lines, i, container, out)
            prev_blank = False
            continue

        item = _LIST_RE.match(body)
        if item is not None:
            marker_indent = _indent_width(item.group("indent"))
            content_indent = (
                marker_indent + len(item.group("marker")) + max(1, len(item.group("space")))
            )
            while stack and marker_indent < stack[-1]:
                stack.pop()
            stack.append(content_indent)
            # `- ```bash` opens a fence on the marker line itself.
            inline_fence = _valid_fence(body[item.end() :])
            if inline_fence is not None:
                i = _consume_fence(lines, i, inline_fence.group("fence"), content_indent, out)
                prev_blank = False
                continue
        else:
            refdef = _REFDEF_RE.match(body)
            if refdef is not None and not stack:
                base = ln.start + qoff
                out.append(
                    Region("ref_def", base + refdef.start("label"), base + refdef.end("dest"))
                )
                if refdef.group("title") is not None:
                    out.append(
                        Region("ref_def", base + refdef.start("quote"), base + refdef.start("inner"))
                    )
                    out.append(
                        Region("ref_def", base + refdef.start("endq"), base + refdef.end("endq"))
                    )
        prev_blank = False
        i += 1


def _free_spans(text: str, regions: list[Region]) -> list[tuple[int, int]]:
    """The complement of `regions` over `text`, in order."""
    spans = []
    pos = 0
    for r in sorted(regions, key=lambda r: (r.start, r.end)):
        if r.start > pos:
            spans.append((pos, r.start))
        pos = max(pos, r.end)
    if pos < len(text):
        spans.append((pos, len(text)))
    return spans


def _pattern_pass(text, regions, pattern, kind, validator=None) -> None:
    """Match `pattern` inside unprotected text only.

    finditer() is given the whole document with pos/endpos bounds, so lookbehind
    assertions still see the characters before the span.
    """
    found = []
    for start, end in _free_spans(text, regions):
        for m in pattern.finditer(text, start, end):
            if m.end() == m.start():
                continue
            if validator is not None and not validator(m):
                continue
            found.append(Region(kind, m.start(), m.end()))
    regions.extend(found)


def _blank_line_ahead(text: str, pos: int, end: int) -> bool:
    """True when text[pos] starts a newline followed by a blank line."""
    if text[pos] != "\n":
        return False
    j = pos + 1
    while j < end and text[j] in " \t":
        j += 1
    return j >= end or text[j] == "\n"


def _scan_code_spans(text: str, regions: list[Region]) -> None:
    """Pair a run of N backticks with the next run of exactly N backticks.

    A code span may cross a newline but never a blank line, because a blank
    line ends the paragraph.
    """
    found = []
    for start, end in _free_spans(text, regions):
        i = start
        while i < end:
            if text[i] != "`":
                i += 1
                continue
            run = 1
            while i + run < end and text[i + run] == "`":
                run += 1
            j = i + run
            close = -1
            while j < end:
                if text[j] == "`":
                    run2 = 1
                    while j + run2 < end and text[j + run2] == "`":
                        run2 += 1
                    if run2 == run:
                        close = j + run2
                        break
                    j += run2
                    continue
                if _blank_line_ahead(text, j, end):
                    break
                j += 1
            if close < 0:
                i += run
                continue
            found.append(Region("code_span", i, close))
            i = close
    regions.extend(found)


_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_RAWTEXT_RE = re.compile(
    r"<(%s)\b[^<>]*>.*?</\1\s*>" % "|".join(RAW_TEXT_ELEMENTS),
    re.DOTALL | re.IGNORECASE,
)
_HTML_DECL_RE = re.compile(r"<![A-Za-z][^>]*>|<\?.*?\?>|<!\[CDATA\[.*?\]\]>", re.DOTALL)
_HTML_TAG_RE = re.compile(
    r"""</?[A-Za-z][A-Za-z0-9-]*
        (?:\s+[A-Za-z_:@#$][\w.:-]*
            (?:\s*=\s*(?:"[^"]*"|'[^']*'|[^\s"'=<>`]+))?
        )*
        \s*/?>""",
    re.VERBOSE,
)
_AUTOLINK_RE = re.compile(r"<[A-Za-z][A-Za-z0-9+.-]{1,31}:[^<>\s]*>|<[^\s<>@]+@[^\s<>]+>")


def _scan_link_destinations(text: str, regions: list[Region]) -> None:
    """Protect `](dest` and the closing `)` of inline links and images.

    The link text stays prose because the reader sees it. The title stays prose
    for the same reason -- it renders as a tooltip -- so only the destination
    and the punctuation around the title are protected.
    """
    found = []
    for start, end in _free_spans(text, regions):
        i = start
        while True:
            j = text.find("](", i, end)
            if j < 0:
                break
            k = j + 2
            if k < end and text[k] == "<":
                close = text.find(">", k, end)
                if close < 0:
                    i = k
                    continue
                dest_end = close + 1
            else:
                depth = 0
                p = k
                while p < end:
                    ch = text[p]
                    if ch.isspace():
                        break
                    if ch == "(":
                        depth += 1
                    elif ch == ")":
                        if depth == 0:
                            break
                        depth -= 1
                    p += 1
                dest_end = p
            p = dest_end
            while p < end and text[p] in " \t\n":
                p += 1
            if p < end and text[p] in "\"'(":
                quote = ")" if text[p] == "(" else text[p]
                q = text.find(quote, p + 1, end)
                if q >= 0:
                    after = q + 1
                    while after < end and text[after] in " \t\n":
                        after += 1
                    if after < end and text[after] == ")":
                        found.append(Region("link_dest", j, p + 1))
                        found.append(Region("link_dest", q, after + 1))
                        i = after + 1
                        continue
            if dest_end < end and text[dest_end] == ")":
                found.append(Region("link_dest", j, dest_end + 1))
                i = dest_end + 1
                continue
            i = j + 2
    regions.extend(found)


_REF_USAGE_RE = re.compile(r"\]\[[^\]\n]*\]")
_SHORTCUT_REF_RE = re.compile(r"\[(?P<label>[^\[\]\n]+)\](?P<collapsed>\[\])?")


def _normalise_label(label: str) -> str:
    """CommonMark label matching: case-insensitive, whitespace collapsed."""
    return " ".join(label.split()).lower()


def _reference_labels(text: str) -> set:
    """Every label defined by a `[label]: dest` line in the document."""
    labels = set()
    for line in _split_lines(text):
        body, _ = _strip_quote(line.text)
        match = _REFDEF_RE.match(body)
        if match is not None:
            labels.add(_normalise_label(match.group("label")[1:-2]))
    return labels


def _scan_shortcut_references(text: str, regions: list) -> None:
    """Protect `[label]` and `[label][]` when `label` is defined.

    A shortcut reference is its own link target: rewriting the visible word
    silently unresolves the link. A `[text][label]` full reference is not
    touched here -- its first bracket is ordinary prose, and its second is
    already protected as a reference usage.
    """
    labels = _reference_labels(text)
    if not labels:
        return
    found = []
    for start, end in _free_spans(text, regions):
        for match in _SHORTCUT_REF_RE.finditer(text, start, end):
            if _normalise_label(match.group("label")) not in labels:
                continue
            after = text[match.end() : match.end() + 1]
            if match.group("collapsed") is None and after in ("(", "["):
                continue  # an inline link or a full reference: the text is prose
            found.append(Region("ref_shortcut", match.start(), match.end()))
    regions.extend(found)
_BARE_URL_RE = re.compile(
    r"""(?<![\w@.-])
        (?: (?:https?|ftps?|file|git|ssh|irc|news)://
          | (?:mailto|tel|sms):
          | www\.)
        [^\s<>()\[\]{}"'`]*[^\s<>()\[\]{}"'`.,;:!?]""",
    re.VERBOSE | re.IGNORECASE,
)

_MATH_BLOCK_RE = re.compile(r"\$\$.+?\$\$", re.DOTALL)
_MATH_INLINE_RE = re.compile(r"(?<![\w$])\$(?!\s)[^$\n]{1,200}?(?<!\s)\$(?![\w$])")

_EMAIL_RE = re.compile(r"(?<![\w.+@-])[\w.+%-]+@[A-Za-z0-9][\w.-]*[\w]")
# Every placeholder syntax a document is likely to quote inline. A single
# brace counts: `{colour}` is a str.format field, not the word in braces.
_TEMPLATE_RE = re.compile(
    r"""\{\{[^{}\n]*\}\}                                  # {{ mustache }}
      | \{%[^\n]*?%\}                                      # {% statement %}
      | \{\#[^\n]*?\#\}                                    # {# comment #}
      | \$\{[^}\n]*\}                                      # ${shell}
      | %\{[^}\n]*\}                                       # %{ruby}
      | %\([A-Za-z_]\w*\)[-+ #0]*\d*(?:\.\d+)?[A-Za-z]     # %(printf)s
      | \{[A-Za-z_][\w.]*(?:\[[^\]\n]*\])?(?:![rsa])?(?::[^{}\n]*)?\}
    """,
    re.VERBOSE,
)
_ENTITY_RE = re.compile(r"&(?:\#\d{1,7}|\#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});")
_ENV_VAR_RE = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*")
_FLAG_RE = re.compile(r"(?<![\w`-])--?[A-Za-z0-9][A-Za-z0-9-]*(?:=[^\s`|]+)?")
_PATH_RE = re.compile(r"(?<![\w./~$-])/?[\w.@$+~-]+(?:/[\w.@$+~-]*)+")
_FILE_EXT_RE = re.compile(r"(?<![\w./-])[\w-]+\.(?:%s)\b" % _FILE_EXTENSIONS, re.IGNORECASE)
_SEMVER_RE = re.compile(r"(?<![\w.])v?\d+\.\d+(?:\.\d+)*(?:[-+][\w.]+)?(?![\w.])")
_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|(?<![\w#])(?=[0-9a-f]*\d)[0-9a-f]{7,40}(?![\w])")
_SNAKE_RE = re.compile(r"(?<![\w`-])_*[A-Za-z0-9]+(?:_+[A-Za-z0-9]+)+_*(?![\w])")
_CAMEL_RE = re.compile(
    r"(?<![\w`-])(?:[a-z][a-z0-9]*(?:[A-Z][A-Za-z0-9]*)+|(?:[A-Z][a-z0-9]+){2,})(?![\w])"
)
_HANDLE_RE = re.compile(r"(?<![\w./-])@[A-Za-z0-9][\w.-]*[\w]")
_HASH_REF_RE = re.compile(r"(?<![\w&#])#(?=[\w-]*\d)[\w-]+")


def _looks_like_path(m: "re.Match") -> bool:
    """Reject prose slashes ('and/or', 'read/write'); accept real paths."""
    token = m.group(0)
    if token.startswith(("/", "./", "../", "~/")):
        return True
    if token.endswith("/"):
        return True
    segments = [s for s in token.split("/") if s]
    if len(segments) >= 3:
        return True
    return any("." in s for s in segments)


_IDENTIFIER_PASSES = (
    ("email", _EMAIL_RE, None),
    ("template_var", _TEMPLATE_RE, None),
    ("env_var", _ENV_VAR_RE, None),
    ("flag", _FLAG_RE, None),
    ("path", _PATH_RE, _looks_like_path),
    ("file_ext", _FILE_EXT_RE, None),
    ("semver", _SEMVER_RE, None),
    ("hex", _HEX_RE, None),
    ("snake_case", _SNAKE_RE, None),
    ("camel_case", _CAMEL_RE, None),
    ("email", _HANDLE_RE, None),
    ("hex", _HASH_REF_RE, None),
    ("entity", _ENTITY_RE, None),
)


def _is_word_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"


def _expand_identifier_regions(text: str, regions: list[Region]) -> None:
    """Glue identifier tokens to word characters they touch.

    `flavour${X}s` is one identifier, not the word 'flavour' plus a variable,
    and rewriting the visible half would corrupt it. Only token kinds are
    expanded: an HTML tag must not swallow its neighbours, or `one<br>colour`
    would hide real prose.
    """
    for idx, region in enumerate(regions):
        if region.kind not in _GLUE_KINDS:
            continue
        start, end = region.start, region.end
        while start > 0 and _is_word_char(text[start - 1]):
            start -= 1
        while end < len(text) and _is_word_char(text[end]):
            end += 1
        if (start, end) != (region.start, region.end):
            regions[idx] = Region(region.kind, start, end)


def _normalise(text: str, regions: list[Region]) -> list[Region]:
    """Sort, merge overlaps, then split every region at newlines."""
    merged: list[Region] = []
    for region in sorted(regions, key=lambda r: (r.start, -r.end)):
        if region.end <= region.start:
            continue
        if merged and region.start <= merged[-1].end:
            last = merged[-1]
            if region.end > last.end:
                merged[-1] = Region(last.kind, last.start, region.end)
            continue
        merged.append(region)

    split: list[Region] = []
    for region in merged:
        start = region.start
        while True:
            nl = text.find("\n", start, region.end)
            if nl < 0:
                break
            if nl > start:
                split.append(Region(region.kind, start, nl))
            start = nl + 1
        if region.end > start:
            split.append(Region(region.kind, start, region.end))
    return split


def find_regions(text: str, mask_math: bool = False) -> list[Region]:
    """Every span of `text` that must survive the conversion unchanged."""
    regions: list[Region] = []
    _scan_sentinels(text, regions)
    _scan_directives(text, regions)
    _scan_blocks(text, regions)
    _scan_code_spans(text, regions)
    _pattern_pass(text, regions, _HTML_COMMENT_RE, "html_comment")
    _pattern_pass(text, regions, _HTML_RAWTEXT_RE, "html_rawtext")
    _pattern_pass(text, regions, _HTML_DECL_RE, "html_decl")
    _pattern_pass(text, regions, _AUTOLINK_RE, "autolink")
    _pattern_pass(text, regions, _HTML_TAG_RE, "html_tag")
    _scan_link_destinations(text, regions)
    _scan_shortcut_references(text, regions)
    _pattern_pass(text, regions, _REF_USAGE_RE, "ref_usage")
    _pattern_pass(text, regions, _BARE_URL_RE, "url")
    if mask_math:
        _pattern_pass(text, regions, _MATH_BLOCK_RE, "math")
        _pattern_pass(text, regions, _MATH_INLINE_RE, "math")
    for kind, pattern, validator in _IDENTIFIER_PASSES:
        _pattern_pass(text, regions, pattern, kind, validator)
    _expand_identifier_regions(text, regions)
    return _normalise(text, regions)


def prose_spans(text: str, regions: "list[Region] | None" = None) -> list[tuple[int, int]]:
    """The complement of find_regions(): the spans a rule may rewrite."""
    if regions is None:
        regions = find_regions(text)
    return _free_spans(text, regions)


def protect(text: str) -> tuple[str, list[str]]:
    """Replace every protected region with a placeholder."""
    regions = find_regions(text)
    parts: list[str] = []
    placeholders: list[str] = []
    pos = 0
    for region in regions:
        if region.start > pos:
            parts.append(text[pos : region.start])
        parts.append(MASK_OPEN + str(len(placeholders)) + MASK_CLOSE)
        placeholders.append(text[region.start : region.end])
        pos = region.end
    parts.append(text[pos:])
    return "".join(parts), placeholders


def restore(masked_text: str, placeholders: list[str]) -> str:
    """Put every protected region back. Raises ValueError on a damaged mask."""
    stripped = _PLACEHOLDER_RE.sub("", masked_text)
    for sentinel in _SENTINELS:
        if sentinel in stripped:
            raise ValueError("damaged placeholder: stray sentinel in masked text")

    def substitute(m: "re.Match") -> str:
        index = int(m.group(1))
        if index >= len(placeholders):
            raise ValueError("damaged placeholder: index %d out of range" % index)
        return placeholders[index]

    return _PLACEHOLDER_RE.sub(substitute, masked_text)


def round_trips(text: str) -> bool:
    """True when masking the document is provably lossless."""
    try:
        return restore(*protect(text)) == text
    except ValueError:
        return False


# ==========================================================================
# Part 2 -- the lexicon
#
# Every table below is closed. There is deliberately no general `-re$ -> -er$`,
# `-our$ -> -or$`, `-lled$ -> -led$`, `ae -> e` or `oe -> e` pattern: four of
# those five destroy common words on the first document they meet (acre, hour,
# controlled, aesthetic). The only open patterns are `-ise`, `-yse` and the
# doubled-`l` suffixes, and each is gated on a stem list or a deny list.
# ==========================================================================

# ---- rule names, used for --no-rule, findings, and the by_rule stats ------

TIER_NAMES = ("ambiguous", "proper-noun")

RULE_NAMES = (
    "our-or",
    "re-er",
    "si-units",
    "ise-ize",
    "yse-yze",
    "ogue-og",
    "ae-oe",
    "ce-se",
    "double-l",
    "single-l",
    "programme",
    "judgment",
    "irregular",
    "iupac",
    "typo",
)

# ---- 1. -our -> -or ------------------------------------------------------
# Closed stem list. A stem may carry a listed prefix and any lowercase suffix,
# so `unfavourable`, `colourway` and `discoloured` all fall out of one entry.

OUR_STEMS = {
    "arbour": "arbor",
    "ardour": "ardor",
    "armour": "armor",
    "behaviour": "behavior",
    "belabour": "belabor",
    "candour": "candor",
    "clamour": "clamor",
    "clangour": "clangor",
    "colour": "color",
    "demeanour": "demeanor",
    "dolour": "dolor",
    "enamour": "enamor",
    "endeavour": "endeavor",
    "favour": "favor",
    "fervour": "fervor",
    "flavour": "flavor",
    "harbour": "harbor",
    "honour": "honor",
    "humour": "humor",
    "labour": "labor",
    "misdemeanour": "misdemeanor",
    "neighbour": "neighbor",
    "odour": "odor",
    "parlour": "parlor",
    "rancour": "rancor",
    "rigour": "rigor",
    "rumour": "rumor",
    "saviour": "savior",
    "savour": "savor",
    "splendour": "splendor",
    "succour": "succor",
    "tumour": "tumor",
    "valour": "valor",
    "vapour": "vapor",
    "vigour": "vigor",
}

# `glamour` is the exception American usage keeps. Only its derived forms lose
# the u, so the bare noun and its plural are left alone.
OUR_SUFFIX_ONLY = {"glamour": "glamor"}
OUR_SUFFIX_ONLY_SUFFIXES = frozenset(
    {"ous", "ously", "ousness", "ise", "ised", "ises", "ising", "isation", "isations"}
)

# Words that end in -our and are identical in both varieties. Never matched,
# because they are not stems -- listed so the selftest can prove it.
OUR_NEVER = frozenset(
    {
        "amour",
        "contour",
        "detour",
        "dour",
        "devour",
        "flour",
        "four",
        "glamour",
        "hour",
        "our",
        "paramour",
        "pour",
        "scour",
        "sour",
        "tour",
        "troubadour",
        "velour",
        "your",
    }
)

# ---- 2. -re -> -er -------------------------------------------------------

RE_STEMS = {
    "accoutre": ("accouter", "re-er"),
    "centre": ("center", "re-er"),
    "fibre": ("fiber", "re-er"),
    "goitre": ("goiter", "re-er"),
    "litre": ("liter", "si-units"),
    "louvre": ("louver", "re-er"),
    "lustre": ("luster", "re-er"),
    "manoeuvre": ("maneuver", "re-er"),
    "meagre": ("meager", "re-er"),
    "metre": ("meter", "si-units"),
    "mitre": ("miter", "re-er"),
    "nitre": ("niter", "re-er"),
    "ochre": ("ocher", "re-er"),
    "philtre": ("philter", "re-er"),
    "reconnoitre": ("reconnoiter", "re-er"),
    "sabre": ("saber", "re-er"),
    "saltpetre": ("saltpeter", "re-er"),
    "sceptre": ("scepter", "re-er"),
    "sepulchre": ("sepulcher", "re-er"),
    "sombre": ("somber", "re-er"),
    "spectre": ("specter", "re-er"),
    "theatre": ("theater", "re-er"),
    "titre": ("titer", "re-er"),
}

RE_PREFIXES = (
    "amphi",
    "lack",
    "centi",
    "deca",
    "deci",
    "epi",
    "femto",
    "giga",
    "hecto",
    "hemi",
    "inter",
    "kilo",
    "macro",
    "mega",
    "micro",
    "milli",
    "mid",
    "multi",
    "nano",
    "out",
    "pico",
    "re",
    "semi",
    "sub",
    "super",
    "tera",
)

# `centre` drops its final e before these suffixes: `centring`, `centred`,
# `manoeuvrability`. The set is closed because `metr` + `ic` and `fibr` + `ous`
# are ordinary words that must not be touched.
RE_DROP_E_SUFFIXES = ("ability", "abilities", "ably", "able", "ings", "ing", "ed")

# Suffixes the stem keeps its final `e` in front of. Closed, so `sombrero` does
# not become `somberro`.
RE_PLAIN_SUFFIXES = (
    "",
    "s",
    "ly",
    "less",
    "lessly",
    "piece",
    "pieces",
    "point",
    "points",
    "board",
    "boards",
    "fold",
    "folds",
    "ness",
    "nesses",
    "line",
    "lines",
    "glass",
    "goer",
    "goers",
    "man",
    "men",
    "wide",
    "work",
    "works",
)

RE_ALL_PREFIXES = ("",) + RE_PREFIXES

RE_NEVER = frozenset(
    {
        "acre",
        "acres",
        "cadre",
        "cadres",
        "chancre",
        "euchre",
        "genre",
        "genres",
        "libre",
        "lucre",
        "macabre",
        "massacre",
        "mediocre",
        "nacre",
        "oeuvre",
        "ogre",
        "ogres",
        "padre",
        "timbre",
        "timbres",
    }
)

# ---- 3. -ise -> -ize -----------------------------------------------------
# An open pattern, gated three ways: the letter before `ise` may not be a
# vowel or w/y, the normalised `-ise` stem may not be in the deny list, and
# the prefix must be at least two letters long.

# Longest first, so `organisationally` never matches as `organisation` + ally.
# Every inflection of a stem has to be here or the same document ends up with
# `recognizable` next to `recognisably`.
ISE_SUFFIXES = (
    ("isationally", "izationally"),
    ("isabilities", "izabilities"),
    ("isational", "izational"),
    ("isability", "izability"),
    ("isations", "izations"),
    ("isements", "izements"),
    ("isingly", "izingly"),
    ("isances", "izances"),
    ("isation", "ization"),
    ("isement", "izement"),
    ("isables", "izables"),
    ("isants", "izants"),
    ("isable", "izable"),
    ("isance", "izance"),
    ("isably", "izably"),
    ("isant", "izant"),
    ("isers", "izers"),
    ("ising", "izing"),
    ("iser", "izer"),
    ("ises", "izes"),
    ("ised", "ized"),
    ("ise", "ize"),
)

ISE_BLOCKED_PRECEDING = frozenset("aeiouwy")

# Nouns that end in `-is` and take an `-ises` plural. `irises` is `iris` + es,
# not `ir` + `ises`, and the letter before `ise` (`r`, `v`, `ll`) says nothing
# about which reading is right -- only the noun list does. Every entry here is
# a word the -ise rule would otherwise turn into a non-word.
ISE_NOUN_STEMS = frozenset(
    {
        "acropolis",
        "adonis",
        "aegis",
        "amaryllis",
        "cannabis",
        "chrysalis",
        "clematis",
        "clitoris",
        "dermis",
        "epidermis",
        "epiglottis",
        "eris",
        "finis",
        "glottis",
        "ibis",
        "iris",
        "mantis",
        "megalopolis",
        "metropolis",
        "necropolis",
        "pelvis",
        "penis",
        "portcullis",
        "praxis",
        "proboscis",
        "pubis",
        "trellis",
        "verdigris",
    }
)

# Personal names ending in -ise are in here too: `Denise` is not a verb, and
# the case-preserving writer would happily produce `Denize`.
ISE_NEVER_STEMS = frozenset(
    {
        "advertise",
        "annalise",
        "cochise",
        "denise",
        "elise",
        "advise",
        "anise",
        "apprise",
        "arise",
        "cerise",
        "chastise",
        "chemise",
        "circumcise",
        "comprise",
        "compromise",
        "concise",
        "crise",
        "demise",
        "despise",
        "devise",
        "enterprise",
        "excise",
        "exercise",
        "exorcise",
        "expertise",
        "franchise",
        "improvise",
        "incise",
        "merchandise",
        "mortise",
        "paradise",
        "precise",
        "premise",
        "prise",
        "promise",
        "reprise",
        "highrise",
        "moonrise",
        "revise",
        "rise",
        "sunrise",
        "supervise",
        "surmise",
        "surprise",
        "televise",
        "treatise",
        "valise",
        "vise",
        "wise",
    }
)

# Prefixes stripped (repeatedly) before the deny check, so `disenfranchise`
# reduces to `franchise` while `organise` does not reduce to `anise`.
WORD_PREFIXES = (
    "counter",
    "hyper",
    "inter",
    "multi",
    "super",
    "ultra",
    "under",
    "over",
    "semi",
    "self",
    "dis",
    "mis",
    "non",
    "out",
    "pre",
    "sub",
    "co",
    "de",
    "en",
    "il",
    "im",
    "in",
    "ir",
    "re",
    "un",
    "up",
)

# The -our stems compound with more than the negating prefixes: `watercolour`
# and `multicoloured` are one word each, and the hyphenated spellings already
# convert because the hyphen splits the token.
OUR_PREFIXES = ("",) + WORD_PREFIXES + (
    "bi",
    "mono",
    "techni",
    "tri",
    "vari",
    "water",
)

# ---- 4. -yse -> -yze -----------------------------------------------------
# `-yses` is deliberately absent: `analyses` is a verb form and a plural noun
# at the same time, so it belongs to the ambiguous tier.

YSE_PREFIXES = frozenset(
    {
        "anal",
        "autol",
        "breathal",
        "catal",
        "dial",
        "electrol",
        "haemol",
        "hemol",
        "hydrol",
        "paral",
        "photol",
        "psychoanal",
        "pyrol",
    }
)

YSE_SUFFIXES = (("ysing", "yzing"), ("ysers", "yzers"), ("yser", "yzer"), ("ysed", "yzed"), ("yse", "yze"))

YSE_NEVER = frozenset(
    {
        "analysis",
        "analyst",
        "analysts",
        "analytic",
        "analytical",
        "catalysis",
        "dialysis",
        "geyser",
        "geysers",
        "lyse",
        "lysed",
        "lyses",
        "lysing",
        "paralysis",
    }
)

# ---- 5. -ogue -> -og -----------------------------------------------------
# Enumerated, never derived: `cataloged` and `cataloging` lose the u as well as
# the ue, which no suffix rule would get right.

OGUE_WORDS = {
    "analogue": "analog",
    "analogues": "analogs",
    "catalogue": "catalog",
    "catalogued": "cataloged",
    "cataloguer": "cataloger",
    "cataloguers": "catalogers",
    "catalogues": "catalogs",
    "cataloguing": "cataloging",
}

OGUE_NEVER = frozenset(
    {
        "brogue",
        "demagogue",
        "epilogue",
        "ideologue",
        "monologue",
        "pedagogue",
        "prologue",
        "rogue",
        "synagogue",
        "travelogue",
        "vogue",
    }
)

# ---- 6. ae / oe digraphs -------------------------------------------------
# Word-initial prefixes first (they carry every inflection for free), then the
# handful of words whose digraph is not at the start.

AE_OE_PREFIXES = (
    ("orthopaed", "orthoped"),
    ("aetiolog", "etiolog"),
    ("anaesth", "anesth"),
    ("gynaec", "gynec"),
    ("oesoph", "esoph"),
    ("palaeo", "paleo"),
    ("haemat", "hemat"),
    ("oestr", "estr"),
    ("haem", "hem"),
    ("paed", "ped"),
)

# Word-final digraphs. `-aemia`, `-rrhoea` and `-oedema` are Greek medical
# endings: nothing else in English ends that way, so the pattern is closed in
# practice even though it is written as a suffix.
AE_OE_SUFFIXES = (
    ("aemias", "emias"),
    ("rrhoeas", "rrheas"),
    ("rrhoeal", "rrheal"),
    ("oedemas", "edemas"),
    ("aemia", "emia"),
    ("aemic", "emic"),
    ("rrhoea", "rrhea"),
    ("oedema", "edema"),
)

AE_OE_WORDS = {
    "anaemia": "anemia",
    "anaemic": "anemic",
    "caesarean": "cesarean",
    "coeliac": "celiac",
    "diarrhoea": "diarrhea",
    "diarrhoeal": "diarrheal",
    "encyclopaedia": "encyclopedia",
    "encyclopaedias": "encyclopedias",
    "encyclopaedic": "encyclopedic",
    "faecal": "fecal",
    "faeces": "feces",
    "foetal": "fetal",
    "foetid": "fetid",
    "foetus": "fetus",
    "foetuses": "fetuses",
    "homoeopathic": "homeopathic",
    "homoeopathy": "homeopathy",
    "leukaemia": "leukemia",
    "mediaeval": "medieval",
    "oedema": "edema",
    "septicaemia": "septicemia",
}

AE_OE_NEVER = frozenset(
    {
        "aegis",
        "aerial",
        "aerobic",
        "aeronautics",
        "aerosol",
        "aerospace",
        "aesthete",
        "aesthetic",
        "aesthetics",
        "algae",
        "amoeba",
        "amoebae",
        "antennae",
        "archaeological",
        "archaeology",
        "coefficient",
        "coerce",
        "coeval",
        "coexist",
        "daemon",
        "daemons",
        "does",
        "formulae",
        "goes",
        "larvae",
        "maestro",
        "onomatopoeia",
        "paella",
        "phoenix",
        "poem",
        "poet",
        "shoe",
        "subpoena",
        "sundae",
        "toe",
        "vertebrae",
    }
)

# ---- 7. -ce / -se nouns and verbs ---------------------------------------

CE_SE_WORDS = {
    "defence": "defense",
    "defenceless": "defenseless",
    "defences": "defenses",
    "licence": "license",
    "licenced": "licensed",
    "licencee": "licensee",
    "licencees": "licensees",
    "licences": "licenses",
    "licencing": "licensing",
    "offence": "offense",
    "offences": "offenses",
    "practise": "practice",
    "practised": "practiced",
    "practises": "practices",
    "practising": "practicing",
    "premiss": "premise",
    "premisses": "premises",
    "pretence": "pretense",
    "pretences": "pretenses",
}

CE_SE_NEVER = frozenset(
    {"absence", "essence", "fence", "hence", "licensed", "license", "practice", "presence", "since"}
)

# ---- 8. doubled final l -------------------------------------------------
# British doubles a final `l` before a suffix regardless of stress. The stems
# are enumerated; the suffix table is what makes `travelled -> traveled` and
# `counsellor -> counselor` one rule.

DOUBLE_L_STEMS = frozenset(
    {
        "apparel",
        "barrel",
        "bushel",
        "bevel",
        "cancel",
        "cavil",
        "channel",
        "chisel",
        "counsel",
        "cruel",
        "cudgel",
        "devil",
        "dial",
        "dishevel",
        "drivel",
        "duel",
        "empanel",
        "enamel",
        "equal",
        "fuel",
        "funnel",
        "gambol",
        "gravel",
        "grovel",
        "impanel",
        "initial",
        "jewel",
        "kennel",
        "kernel",
        "label",
        "level",
        "libel",
        "marshal",
        "marvel",
        "medal",
        "metal",
        "model",
        "panel",
        "parallel",
        "pedal",
        "pencil",
        "pummel",
        "quarrel",
        "ravel",
        "revel",
        "rival",
        "scalpel",
        "shovel",
        "shrivel",
        "signal",
        "snivel",
        "snorkel",
        "spiral",
        "squirrel",
        "stencil",
        "swivel",
        "tassel",
        "tinsel",
        "total",
        "trammel",
        "travel",
        "trial",
        "trowel",
        "tunnel",
        "unravel",
        "victual",
        "weasel",
        "wool",
        "yodel",
    }
)

# British form -> American form, as (suffix seen, suffix written). The British
# suffix always starts with the doubled `l`, so the stem left behind already
# ends in a single `l`: `travel` + `led` -> `travel` + `ed`.
DOUBLE_L_SUFFIXES = (
    ("lousness", "ousness"),
    ("lously", "ously"),
    ("lings", "ings"),
    ("lists", "ists"),
    ("lers", "ers"),
    ("lors", "ors"),
    ("lens", "ens"),
    ("lous", "ous"),
    ("ling", "ing"),
    ("list", "ist"),
    ("led", "ed"),
    ("ler", "er"),
    ("lor", "or"),
    ("len", "en"),
)

# Stems that are single-`l`-final in both varieties. They must never enter
# DOUBLE_L_STEMS, or `controlled` would become `controled`.
DOUBLE_L_NEVER = frozenset(
    {
        "annul",
        "appal",
        "bill",
        "call",
        "compel",
        "control",
        "dispel",
        "distil",
        "drill",
        "dwell",
        "enrol",
        "enthral",
        "excel",
        "expel",
        "fill",
        "fulfil",
        "impel",
        "instal",
        "install",
        "instil",
        "kill",
        "mill",
        "patrol",
        "poll",
        "propel",
        "pull",
        "rebel",
        "roll",
        "scroll",
        "skill",
        "smell",
        "spell",
        "stall",
        "swell",
    }
)

# ---- 9. final single l -> ll --------------------------------------------
# A closed list of nine stems, never a pattern. `annul`, `control`, `patrol`,
# `compel` and friends are single-`l`-final in both varieties.

SINGLE_L_WORDS = {
    "appal": "appall",
    "appals": "appalls",
    "distil": "distill",
    "distils": "distills",
    "enrol": "enroll",
    "enrolment": "enrollment",
    "enrolments": "enrollments",
    "enrols": "enrolls",
    "enthral": "enthrall",
    "enthrals": "enthralls",
    "fulfil": "fulfill",
    "fulfilment": "fulfillment",
    "fulfilments": "fulfillments",
    "fulfils": "fulfills",
    "instal": "install",
    "instalment": "installment",
    "instalments": "installments",
    "instals": "installs",
    "instil": "instill",
    "instilment": "instillment",
    "instils": "instills",
    "skilful": "skillful",
    "skilfully": "skillfully",
    "wilful": "willful",
    "wilfully": "willfully",
}

# ---- 10. -mme and -dgement ----------------------------------------------

PROGRAMME_WORDS = {
    "centigramme": "centigram",
    "centigrammes": "centigrams",
    "gramme": "gram",
    "grammes": "grams",
    "kilogramme": "kilogram",
    "kilogrammes": "kilograms",
    "microgramme": "microgram",
    "microgrammes": "micrograms",
    "milligramme": "milligram",
    "milligrammes": "milligrams",
    "programme": "program",
    "programmes": "programs",
    "reprogramme": "reprogram",
    "reprogrammes": "reprograms",
}

JUDGMENT_WORDS = {
    "abridgement": "abridgment",
    "abridgements": "abridgments",
    "acknowledgement": "acknowledgment",
    "acknowledgements": "acknowledgments",
    "judgement": "judgment",
    "judgemental": "judgmental",
    "judgementally": "judgmentally",
    "judgements": "judgments",
    "lodgement": "lodgment",
    "lodgements": "lodgments",
    "misjudgement": "misjudgment",
    "misjudgements": "misjudgments",
    "prejudgement": "prejudgment",
    "prejudgements": "prejudgments",
}

# ---- 11. irregular one-offs ---------------------------------------------

IRREGULAR_WORDS = {
    "aerofoil": "airfoil",
    "aerofoils": "airfoils",
    "aeroplane": "airplane",
    "aeroplanes": "airplanes",
    "ageing": "aging",
    "almanack": "almanac",
    "almanacks": "almanacs",
    "amongst": "among",
    "artefact": "artifact",
    "artefacts": "artifacts",
    "baulk": "balk",
    "baulked": "balked",
    "baulking": "balking",
    "baulks": "balks",
    "behove": "behoove",
    "behoved": "behooved",
    "behoves": "behooves",
    "behoving": "behooving",
    "callisthenic": "calisthenic",
    "callisthenics": "calisthenics",
    "carburetter": "carburetor",
    "carburetters": "carburetors",
    "carburettor": "carburetor",
    "carburettors": "carburetors",
    "cheque": "check",
    "chequebook": "checkbook",
    "chequebooks": "checkbooks",
    "chequer": "checker",
    "chequerboard": "checkerboard",
    "chequerboards": "checkerboards",
    "chequered": "checkered",
    "chequering": "checkering",
    "chequers": "checkers",
    "chequing": "checking",
    "cheques": "checks",
    "connexion": "connection",
    "connexions": "connections",
    "cypher": "cipher",
    "cyphered": "ciphered",
    "cyphering": "ciphering",
    "cyphers": "ciphers",
    "dependant": "dependent",
    "dependants": "dependents",
    "disorientate": "disorient",
    "disorientated": "disoriented",
    "disorientates": "disorients",
    "disorientating": "disorienting",
    "downdraught": "downdraft",
    "downdraughts": "downdrafts",
    "cosier": "cozier",
    "cosiest": "coziest",
    "cosily": "cozily",
    "cosiness": "coziness",
    "cosy": "cozy",
    "draught": "draft",
    "draughted": "drafted",
    "draughtier": "draftier",
    "draughtiest": "draftiest",
    "draughtiness": "draftiness",
    "draughting": "drafting",
    "draughtsman": "draftsman",
    "draughtsmanship": "draftsmanship",
    "draughtsmen": "draftsmen",
    "draughty": "drafty",
    "enquire": "inquire",
    "enquired": "inquired",
    "enquires": "inquires",
    "enquiries": "inquiries",
    "enquiring": "inquiring",
    "enquiry": "inquiry",
    "eyrie": "aerie",
    "eyries": "aeries",
    "flautist": "flutist",
    "flautists": "flutists",
    "furore": "furor",
    "furores": "furors",
    "gaol": "jail",
    "gaoled": "jailed",
    "gaoler": "jailer",
    "gaolers": "jailers",
    "gaoling": "jailing",
    "gaols": "jails",
    "grey": "gray",
    "greyed": "grayed",
    "greying": "graying",
    "greyish": "grayish",
    "greyness": "grayness",
    "greys": "grays",
    "greyscale": "grayscale",
    "greyscales": "grayscales",
    "groyne": "groin",
    "groynes": "groins",
    "inflexion": "inflection",
    "inflexions": "inflections",
    "jeweller": "jeweler",
    "jewellers": "jewelers",
    "jewellery": "jewelry",
    "kerb": "curb",
    "kerbed": "curbed",
    "kerbing": "curbing",
    "kerbs": "curbs",
    "kerbside": "curbside",
    "liquorice": "licorice",
    "maths": "math",
    "mollusc": "mollusk",
    "molluscs": "mollusks",
    "mould": "mold",
    "moulded": "molded",
    "moulder": "molder",
    "mouldered": "moldered",
    "mouldering": "moldering",
    "moulders": "molders",
    "mouldier": "moldier",
    "mouldiest": "moldiest",
    "mouldiness": "moldiness",
    "moulding": "molding",
    "mouldings": "moldings",
    "moulds": "molds",
    "mouldy": "moldy",
    "moult": "molt",
    "moulted": "molted",
    "moulting": "molting",
    "moults": "molts",
    "moustache": "mustache",
    "moustaches": "mustaches",
    "multistorey": "multistory",
    "multistoreys": "multistories",
    "nett": "net",
    "nought": "naught",
    "noughts": "naughts",
    "orientate": "orient",
    "orientated": "oriented",
    "orientates": "orients",
    "orientating": "orienting",
    "pyjama": "pajama",
    "pyjamas": "pajamas",
    "queueing": "queuing",
    "rouble": "ruble",
    "roubles": "rubles",
    "sceptic": "skeptic",
    "sceptical": "skeptical",
    "sceptically": "skeptically",
    "sceptics": "skeptics",
    "scepticism": "skepticism",
    "sizeable": "sizable",
    "smoulder": "smolder",
    "smouldered": "smoldered",
    "smouldering": "smoldering",
    "smoulders": "smolders",
    "storey": "story",
    "storeys": "stories",
    "titbit": "tidbit",
    "titbits": "tidbits",
    "tranquillise": "tranquilize",
    "tranquilliser": "tranquilizer",
    "tranquillisers": "tranquilizers",
    "tranquillity": "tranquility",
    "tyre": "tire",
    "tyres": "tires",
    "updraught": "updraft",
    "updraughts": "updrafts",
    "verandah": "veranda",
    "verandahs": "verandas",
    "waggon": "wagon",
    "waggoner": "wagoner",
    "waggoners": "wagoners",
    "waggons": "wagons",
    "whilst": "while",
    "yoghourt": "yogurt",
    "yoghurt": "yogurt",
    "yoghurts": "yogurts",
}

# Chemistry names where IUPAC and American usage disagree. Grouped so a
# metrology or chemistry document can opt out with `--no-rule iupac`.
# `sulphur -> sulfur` is deliberately not here: IUPAC and American usage agree.
IUPAC_WORDS = {
    "aluminium": "aluminum",
    "aluminiums": "aluminums",
    "caesium": "cesium",
}

# Misspellings that are neither British nor American, fixed in passing.
TYPO_WORDS = {
    "benefitted": "benefited",
    "benefitting": "benefiting",
    "biassed": "biased",
    "biasses": "biases",
    "biassing": "biasing",
    "combatted": "combated",
    "combatting": "combating",
    "focussed": "focused",
    "focusses": "focuses",
    "focussing": "focusing",
    "targetted": "targeted",
    "targetting": "targeting",
}

# Substrings that are unambiguous wherever they appear inside a word.
SUBSTRING_RULES = (("sulph", "sulf"), ("plough", "plow"))

# ---- the ambiguous tier --------------------------------------------------
# Reported, never applied without --aggressive, because both readings are live.

AMBIGUOUS = {
    "analyses": ("analyzes", "verb form or plural of analysis"),
    "autolyse": ("autolyze", "a baking term is often left in the French spelling"),
    "burnt": ("burned", "burnt is a standard American adjective"),
    "calibre": ("caliber", "calibre is also the name of the e-book tool"),
    "calibres": ("calibers", "calibre is also the name of the e-book tool"),
    "catalyses": ("catalyzes", "verb form or plural of catalysis"),
    "dialogue": ("dialog", "dialog is only the UI element"),
    "dialogues": ("dialogs", "dialog is only the UI element"),
    "dialyses": ("dialyzes", "verb form or plural of dialysis"),
    "disc": ("disk", "disc is correct for optical media"),
    "discs": ("disks", "disc is correct for optical media"),
    "draughts": ("drafts", "draughts is also the board game"),
    "dreamt": ("dreamed", "dreamt is acceptable in American English"),
    "electrolyses": ("electrolyzes", "verb form or plural of electrolysis"),
    "greylist": ("graylist", "greylist is the established mail-server term"),
    "greylisting": ("graylisting", "greylist is the established mail-server term"),
    "greylists": ("graylists", "greylist is the established mail-server term"),
    "homologue": ("homolog", "chemistry keeps the -ogue spelling"),
    "homologues": ("homologs", "chemistry keeps the -ogue spelling"),
    "hydrolyses": ("hydrolyzes", "verb form or plural of hydrolysis"),
    "leapt": ("leaped", "leapt is acceptable in American English"),
    "learnt": ("learned", "learnt is acceptable in American English"),
    "paralyses": ("paralyzes", "verb form or plural of paralysis"),
    "prise": ("pry", "prise and prize are different verbs"),
    "prised": ("pried", "prise and prize are different verbs"),
    "prises": ("pries", "prise and prize are different verbs"),
    "prising": ("prying", "prise and prize are different verbs"),
    "smelt": ("smelled", "smelt is also a metallurgy verb"),
    "speciality": ("specialty", "speciality survives in medical usage"),
    "specialities": ("specialties", "speciality survives in medical usage"),
    "spelt": ("spelled", "spelt is also a grain"),
    "spoilt": ("spoiled", "spoilt is a standard American adjective"),
    "storeyed": ("storied", "storied has a second, unrelated meaning"),
    "tonne": ("ton", "a tonne is not a US ton"),
    "unlearnt": ("unlearned", "unlearnt is acceptable in American English"),
    "vice": ("vise", "vice is also a moral failing and a job title"),
}

# `-yses` forms that are not in AMBIGUOUS by name are generated by the -yse
# rule, which reports them rather than converting them.

# ---- names, phrases and context -----------------------------------------

# Fixed names. Matched case-insensitively across word boundaries; every token
# inside a match is skipped with no finding at all.
PROTECTED_PHRASES = (
    ("fibre", "channel"),
    ("labour", "party"),
    ("open", "government", "licence"),
    ("compact", "disc"),
    ("compact", "discs"),
)

# Single tokens that no rule may reach, at any casing. `daemon` is not British
# at all -- it is listed as a standing guard against an over-eager digraph rule
# turning it into `demon`.
NEVER_TOUCH = frozenset({"libre", "daemon", "daemons", "fibre-channel"})

# Capitalised forms that are almost always names. Demoted to the proper-noun
# tier whenever they appear capitalised, reported but never written.
PROPER_WHEN_CAPITALISED = frozenset(
    {"spectre", "sabre", "louvre", "tyre", "grey", "calibre", "mitre"}
)

# Lowercase words that hold a name together. `Ministry of Defence` is one name
# even though `of` breaks the run of capitals.
NAME_CONNECTORS = frozenset(
    {"of", "for", "and", "the", "de", "des", "du", "la", "le", "van", "von", "upon"}
)

# Multi-word conversions, keyed on the lowercase token sequence.
PHRASE_RULES = {("per", "cent"): ("percent", "irregular")}

# An ambiguous word promoted to certain by the word before it.
CONTEXT_BY_PREVIOUS = {
    ("hard", "disc"): "disk",
    ("hard", "discs"): "disks",
    ("floppy", "disc"): "disk",
    ("floppy", "discs"): "disks",
    ("boot", "disc"): "disk",
    ("ram", "disc"): "disk",
}

# An ambiguous word promoted to certain by the word after it.
CONTEXT_BY_NEXT = {
    ("dialogue", "box"): "dialog",
    ("dialogue", "boxes"): "dialog",
    ("dialogues", "boxes"): "dialogs",
}


# ==========================================================================
# Part 3 -- the rule engine
# ==========================================================================


@dataclass(frozen=True)
class Conversion:
    """One token's verdict: what it becomes, under which rule, and how sure."""

    american: str
    rule: str
    ambiguous: bool = False
    reason: str = ""


def _strip_word_prefix(word: str) -> list:
    """Every remainder left by stripping one leading prefix from `word`.

    All of them, not the first that matches: `inter` and `in` both prefix
    `international`, and only one of the two paths reaches a listed stem.
    """
    return [
        word[len(prefix) :]
        for prefix in WORD_PREFIXES
        if word.startswith(prefix) and len(word) - len(prefix) >= 4
    ]


def _reduces_to(word: str, deny: frozenset) -> bool:
    """True when `word`, after stripping up to three prefixes, hits `deny`."""
    frontier = [word]
    seen = {word}
    for _ in range(4):
        if not frontier:
            return False
        nxt = []
        for candidate in frontier:
            if candidate in deny:
                return True
            for shorter in _strip_word_prefix(candidate):
                if shorter not in seen:
                    seen.add(shorter)
                    nxt.append(shorter)
        frontier = nxt
    return False


# Every -our stem contains `our`, and every -re stem contains `r`. Both are
# one substring test that skips the whole table for most words in a document.
def _apply_our(word: str) -> "Conversion | None":
    """-our -> -or, over a closed stem list with optional prefix and suffix."""
    if "our" not in word:
        return None
    for prefix in OUR_PREFIXES:
        if prefix and not word.startswith(prefix):
            continue
        rest = word[len(prefix) :]
        for stems, suffix_filter in (
            (OUR_STEMS, None),
            (OUR_SUFFIX_ONLY, OUR_SUFFIX_ONLY_SUFFIXES),
        ):
            for stem, american in stems.items():
                if not rest.startswith(stem):
                    continue
                suffix = rest[len(stem) :]
                if suffix_filter is not None and suffix not in suffix_filter:
                    continue
                return Conversion(prefix + american + suffix, "our-or")
    return None


def _apply_re(word: str) -> "Conversion | None":
    """-re -> -er, over a closed stem list. Drop-e forms are handled first."""
    if "r" not in word:
        return None
    for prefix in RE_ALL_PREFIXES:
        if prefix and not word.startswith(prefix):
            continue
        rest = word[len(prefix) :]
        for stem, (american, rule) in RE_STEMS.items():
            if rest.startswith(stem[:-1]) and len(rest) > len(stem) - 1:
                tail = rest[len(stem) - 1 :]
                if tail in RE_DROP_E_SUFFIXES:
                    return Conversion(prefix + american + tail, rule)
            if rest.startswith(stem) and rest[len(stem) :] in RE_PLAIN_SUFFIXES:
                return Conversion(prefix + american + rest[len(stem) :], rule)
    return None


def _apply_ise(word: str) -> "Conversion | None":
    """-ise -> -ize, gated on the preceding letter and two deny lists."""
    if "is" not in word:
        return None
    for british, american in ISE_SUFFIXES:
        if not word.endswith(british):
            continue
        stem = word[: -len(british)]
        if len(stem) < 2:
            return None
        if stem[-1] in ISE_BLOCKED_PRECEDING:
            return None
        # `irises` is the plural of a noun, not a verb form: the suffix split
        # is `iris` + `es`, so there is no -ise verb here to convert.
        if _reduces_to(stem + "is", ISE_NOUN_STEMS):
            return None
        if _reduces_to(stem + "ise", ISE_NEVER_STEMS):
            return None
        return Conversion(stem + american, "ise-ize")
    return None


def _apply_yse(word: str) -> "Conversion | None":
    """-yse -> -yze, over a closed prefix list. `-yses` is reported, not applied."""
    if word.endswith("yses"):
        stem = word[:-4]
        if _reduces_to(stem, YSE_PREFIXES):
            return Conversion(
                stem + "yzes", "ambiguous", True, "verb form or plural of the -ysis noun"
            )
        return None
    for british, american in YSE_SUFFIXES:
        if not word.endswith(british):
            continue
        stem = word[: -len(british)]
        if not _reduces_to(stem, YSE_PREFIXES):
            return None
        return Conversion(stem + american, "yse-yze")
    return None


def _apply_double_l(word: str) -> "Conversion | None":
    """A doubled final `l` before a suffix collapses to a single `l`."""
    if "l" not in word:
        return None
    for british, american in DOUBLE_L_SUFFIXES:
        if not word.endswith(british):
            continue
        stem = word[: -len(british)]
        if not stem.endswith("l"):
            continue
        if not _reduces_to(stem, DOUBLE_L_STEMS):
            continue
        return Conversion(stem + american, "double-l")
    return None


def _apply_prefix_table(word: str, table, rule: str) -> "Conversion | None":
    """Rewrite a word-initial digraph prefix, keeping every inflection."""
    for british, american in table:
        if word.startswith(british) and len(word) > len(british):
            return Conversion(american + word[len(british) :], rule)
    return None


def _apply_suffix_table(word: str, table, rule: str) -> "Conversion | None":
    """Rewrite a word-final digraph, keeping whatever stem carries it."""
    for british, american in table:
        if word.endswith(british) and len(word) - len(british) >= 2:
            return Conversion(word[: -len(british)] + american, rule)
    return None


def _apply_substrings(word: str) -> "Conversion | None":
    """Rewrite a substring that is unambiguous wherever it appears."""
    for british, american in SUBSTRING_RULES:
        if british in word:
            return Conversion(word.replace(british, american), "irregular")
    return None


EXACT_TABLES = (
    (OGUE_WORDS, "ogue-og"),
    (AE_OE_WORDS, "ae-oe"),
    (CE_SE_WORDS, "ce-se"),
    (SINGLE_L_WORDS, "single-l"),
    (PROGRAMME_WORDS, "programme"),
    (JUDGMENT_WORDS, "judgment"),
    (IRREGULAR_WORDS, "irregular"),
    (IUPAC_WORDS, "iupac"),
    (TYPO_WORDS, "typo"),
)

NEVER_CONVERT = (
    NEVER_TOUCH
    | OUR_NEVER
    | RE_NEVER
    | YSE_NEVER
    | OGUE_NEVER
    | AE_OE_NEVER
    | CE_SE_NEVER
)


def _apply_once(word: str) -> "Conversion | None":
    """The first rule that fires on `word`, or None."""
    for table, rule in EXACT_TABLES:
        if word in table:
            return Conversion(table[word], rule)
    found = _apply_prefix_table(word, AE_OE_PREFIXES, "ae-oe")
    if found is not None:
        return found
    found = _apply_suffix_table(word, AE_OE_SUFFIXES, "ae-oe")
    if found is not None:
        return found
    found = _apply_substrings(word)
    if found is not None:
        return found
    for rule_fn in (_apply_our, _apply_re, _apply_double_l, _apply_ise, _apply_yse):
        found = rule_fn(word)
        if found is not None:
            return found
    return None


def convert_word(word: str, disabled: frozenset = frozenset()) -> "Conversion | None":
    """Convert one lowercase word, composing rules until it stops changing.

    `colourise` needs -our then -ise; `haemolyse` needs the digraph prefix then
    -yse; `desulphurisation` needs the substring rule then -ise. The rule name
    reported is the first one that fired.
    """
    if word in NEVER_CONVERT:
        return None
    if word in AMBIGUOUS:
        if "ambiguous" in disabled:
            return None
        american, reason = AMBIGUOUS[word]
        return Conversion(american, "ambiguous", True, reason)

    current = word
    first_rule = ""
    ambiguous = False
    reason = ""
    for _ in range(5):
        found = _apply_once(current)
        if found is None:
            break
        if found.american == current:
            break
        current = found.american
        if not first_rule:
            first_rule = found.rule
        if found.ambiguous:
            ambiguous = True
            reason = found.reason
            break
    if current == word or not first_rule:
        return None
    if first_rule in disabled:
        return None
    rule = "ambiguous" if ambiguous else first_rule
    if rule in disabled:
        return None
    return Conversion(current, rule, ambiguous, reason)


# ---- case handling -------------------------------------------------------

CASE_LOWER = "lower"
CASE_TITLE = "title"
CASE_UPPER = "upper"


def case_pattern(token: str) -> "str | None":
    """lower / title / upper, or None when the token is identifier-shaped."""
    if token.islower():
        return CASE_LOWER
    if token.isupper() and len(token) > 1:
        return CASE_UPPER
    if token[0].isupper() and token[1:].islower():
        return CASE_TITLE
    return None


def apply_case(american: str, pattern: str) -> str:
    """Re-case a conversion to match the token it replaces."""
    if pattern == CASE_UPPER:
        return american.upper()
    if pattern == CASE_TITLE:
        return american[:1].upper() + american[1:]
    return american


# ---- per-token identifier guard -----------------------------------------

RUN_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_./\\@:$%~+-")
# Sentence punctuation and emphasis underscores are trimmed from a run before
# it is compared with the token, so `colour.` and `_colour_` stay prose while
# `colour.value` and `colour_scheme` do not.
RUN_TRIM = ".,:;!?_"
CONNECTOR_BEFORE = frozenset("-./\\@$%#:")


def _surrounding_run(text: str, start: int, end: int) -> str:
    """The maximal identifier-ish run around [start, end), sentence punctuation trimmed."""
    left = start
    while left > 0 and text[left - 1] in RUN_CHARS:
        left -= 1
    right = end
    while right < len(text) and text[right] in RUN_CHARS:
        right += 1
    run = text[left:right]
    return run.strip(RUN_TRIM)


def _is_prose_hyphenation(run: str) -> bool:
    """True for `behaviour-driven`, false for `X-Colour-Scheme` and `--colour-out`."""
    if run.startswith("-") or run.endswith("-"):
        return False
    segments = run.split("-")
    if len(segments) < 2:
        return False
    if not all(seg.isalpha() for seg in segments):
        return False
    patterns = [case_pattern(seg) for seg in segments]
    if any(p is None for p in patterns):
        return False
    if all(p == CASE_LOWER for p in patterns):
        return True
    if all(p == CASE_UPPER for p in patterns):
        return True
    return patterns[0] == CASE_TITLE and all(p == CASE_LOWER for p in patterns[1:])


def looks_like_identifier(text: str, start: int, end: int) -> bool:
    """True when the token at [start, end) must be left alone as an identifier."""
    token = text[start:end]
    if case_pattern(token) is None:
        return True
    before = text[start - 1] if start > 0 else ""
    if before in CONNECTOR_BEFORE and not (
        before == "-" and _is_prose_hyphenation(_surrounding_run(text, start, end))
    ):
        return True
    after = text[end] if end < len(text) else ""
    if after and after in "(=\\":
        return True
    if after in "./:" and end + 1 < len(text) and text[end + 1].isalnum():
        return True
    run = _surrounding_run(text, start, end)
    if run != token and not _is_prose_hyphenation(run):
        return True
    return False


# ==========================================================================
# Part 4 -- the findings model
# ==========================================================================


@dataclass
class Finding:
    """One place a rewrite is offered, anchored to the original text."""

    path: str
    start: int
    end: int
    line: int
    col: int
    british: str
    american: str
    rule: str
    ambiguous: bool
    in_blockquote: bool
    reason: str
    context: str


@dataclass
class Stats:
    """Counters accumulated across every scanned file."""

    files: int = 0
    skipped_files: int = 0
    findings: int = 0
    convertible: int = 0
    ambiguous: int = 0
    proper_noun: int = 0
    identifier_skip: int = 0
    by_rule: dict = field(default_factory=dict)

    def record(self, finding: Finding) -> None:
        self.findings += 1
        if finding.rule == "proper-noun":
            self.proper_noun += 1
        elif finding.ambiguous:
            self.ambiguous += 1
        else:
            self.convertible += 1
        self.by_rule[finding.rule] = self.by_rule.get(finding.rule, 0) + 1

    def as_dict(self) -> dict:
        return {
            "files": self.files,
            "skipped_files": self.skipped_files,
            "findings": self.findings,
            "convertible": self.convertible,
            "ambiguous": self.ambiguous,
            "proper_noun": self.proper_noun,
            "identifier_skip": self.identifier_skip,
            "by_rule": dict(sorted(self.by_rule.items())),
        }


# Unicode letters count, so `colour\u00e9` is one token and not the word
# `colour` next to a stray letter. Such a token is skipped rather than
# converted: it is not an English word, whatever it is.
_WORD_RE = re.compile(r"[^\W\d_]+")

# Two tokens are in the same phrase when only spaces, emphasis markers and at
# most one line break separate them. Prose wraps, so `Erasmus\nProgramme` has
# to read as one name; a blank line or any punctuation breaks the run.
_ADJACENT_RE = re.compile(r"[ \t*_]*\n?[ \t*_]*")


@dataclass(frozen=True)
class _Token:
    start: int
    end: int
    text: str


def _collect_tokens(text: str, spans: list[tuple[int, int]]) -> list[_Token]:
    """Every prose word token, in document order."""
    tokens = []
    for start, end in spans:
        for m in _WORD_RE.finditer(text, start, end):
            tokens.append(_Token(m.start(), m.end(), m.group(0)))
    return tokens


def _is_title_case(token: str) -> bool:
    return len(token) > 1 and token[0].isupper() and token[1:].islower()


def _adjacent(text: str, left: _Token, right: _Token) -> bool:
    """True when two tokens sit in the same phrase, with only spaces between."""
    between = text[left.end : right.start]
    if not between or len(between) > 5:
        return False
    return _ADJACENT_RE.fullmatch(between) is not None


def _in_blockquote(text: str, offset: int) -> bool:
    bol = text.rfind("\n", 0, offset) + 1
    return _QUOTE_PREFIX_RE.match(text[bol:offset]) is not None


def _context_line(text: str, offset: int) -> str:
    bol = text.rfind("\n", 0, offset) + 1
    eol = text.find("\n", offset)
    if eol < 0:
        eol = len(text)
    return text[bol:eol].strip()[:160]


def _phrase_at(tokens: list[_Token], index: int, text: str, phrase: tuple) -> bool:
    """True when `phrase` matches the token run starting at `index`."""
    if index + len(phrase) > len(tokens):
        return False
    for offset, want in enumerate(phrase):
        if tokens[index + offset].text.lower() != want:
            return False
        if offset and not _adjacent(text, tokens[index + offset - 1], tokens[index + offset]):
            return False
    return True


def scan_text(text: str, path: str, disabled: frozenset = frozenset()) -> tuple[list[Finding], Stats]:
    """Every finding in one document, with the counters gathered along the way."""
    stats = Stats()
    stats.files = 1
    if SKIP_FILE_RE.search("\n".join(text.splitlines()[:20])):
        stats.skipped_files = 1
        return [], stats

    spans = prose_spans(text)
    tokens = _collect_tokens(text, spans)
    findings: list[Finding] = []

    protected_until = -1  # token index; set by a PROTECTED_PHRASES match
    index = 0
    while index < len(tokens):
        token = tokens[index]
        lower = token.text.lower()

        if not token.text.isascii():
            index += 1
            continue
        if index <= protected_until:
            index += 1
            continue
        matched = False
        for phrase in PROTECTED_PHRASES:
            if _phrase_at(tokens, index, text, phrase):
                protected_until = index + len(phrase) - 1
                matched = True
                break
        if matched:
            index += 1
            continue

        pattern = case_pattern(token.text)
        if looks_like_identifier(text, token.start, token.end):
            stats.identifier_skip += 1
            index += 1
            continue

        # Multi-word rules run before single tokens so `per cent` beats `cent`.
        phrase_hit = None
        for phrase, (american, phrase_rule) in PHRASE_RULES.items():
            if phrase_rule in disabled:
                continue
            if _phrase_at(tokens, index, text, phrase):
                phrase_hit = (phrase, american, phrase_rule)
                break
        if phrase_hit is not None:
            phrase, american, phrase_rule = phrase_hit
            last = tokens[index + len(phrase) - 1]
            finding = _make_finding(
                text,
                path,
                token.start,
                last.end,
                apply_case(american, pattern),
                phrase_rule,
                False,
                "",
            )
            findings.append(finding)
            stats.record(finding)
            index += len(phrase)
            continue

        conversion = convert_word(lower, disabled)
        if conversion is None:
            index += 1
            continue

        # Context can promote an ambiguous word to a certain one.
        previous = tokens[index - 1].text.lower() if index else ""
        following = tokens[index + 1].text.lower() if index + 1 < len(tokens) else ""
        promoted = CONTEXT_BY_PREVIOUS.get((previous, lower))
        if promoted is None:
            promoted = CONTEXT_BY_NEXT.get((lower, following))
        if promoted is not None:
            conversion = Conversion(promoted, "irregular")

        rule = conversion.rule
        ambiguous = conversion.ambiguous
        if pattern in (CASE_TITLE, CASE_UPPER) and not ambiguous:
            if _is_proper_noun(text, tokens, index, lower, pattern):
                rule = "proper-noun"
                ambiguous = True
        if rule in disabled:
            index += 1
            continue

        finding = _make_finding(
            text,
            path,
            token.start,
            token.end,
            apply_case(conversion.american, pattern),
            rule,
            ambiguous,
            conversion.reason,
        )
        findings.append(finding)
        stats.record(finding)
        index += 1

    return findings, stats


def _name_neighbour(text: str, tokens: list[_Token], index: int, step: int) -> bool:
    """True when a capitalised token sits next to `index` in the same name.

    One lowercase connector may stand between them, so `Ministry of Defence`
    reads as a single name. Anything else -- punctuation, a blank line, a
    second connector -- ends the run.
    """
    position = index
    for _ in range(2):
        nxt = position + step
        if not 0 <= nxt < len(tokens):
            return False
        left, right = (nxt, position) if step < 0 else (position, nxt)
        if not _adjacent(text, tokens[left], tokens[right]):
            return False
        word = tokens[nxt].text
        if _is_title_case(word):
            return True
        if word.islower() and word in NAME_CONNECTORS:
            position = nxt
            continue
        return False
    return False


def _is_proper_noun(
    text: str, tokens: list[_Token], index: int, lower: str, pattern: str
) -> bool:
    """True when a capitalised candidate is probably part of a name.

    A run of two or more consecutive capitalised words is a name. Sentence
    position does not rescue the first word of a run -- `Encyclopaedia
    Britannica` is a name wherever it appears -- but a capitalised word
    followed by a lowercase one converts normally.

    An ALL-CAPS token is only demoted when the word itself is a known name
    (`MITRE`, `SPECTRE`); the neighbour rule cannot help there, because every
    word in a shouted heading is capitalised.
    """
    if pattern == CASE_UPPER:
        return lower in PROPER_WHEN_CAPITALISED
    if pattern != CASE_TITLE:
        return False
    if lower in PROPER_WHEN_CAPITALISED:
        return True
    return _name_neighbour(text, tokens, index, -1) or _name_neighbour(
        text, tokens, index, 1
    )


def _make_finding(
    text: str,
    path: str,
    start: int,
    end: int,
    american: str,
    rule: str,
    ambiguous: bool,
    reason: str,
) -> Finding:
    line, col = line_col(text, start)
    return Finding(
        path=path,
        start=start,
        end=end,
        line=line,
        col=col,
        british=text[start:end],
        american=american,
        rule=rule,
        ambiguous=ambiguous,
        in_blockquote=_in_blockquote(text, start),
        reason=reason,
        context=_context_line(text, start),
    )


def apply_findings(text: str, findings: list[Finding], aggressive: bool = False) -> str:
    """Splice the applicable findings into the original text.

    Proper-noun demotions are never applied. Ambiguous findings are applied
    only under --aggressive. Editing the original by offset keeps line endings
    and the trailing newline exactly as they were.
    """
    parts = []
    pos = 0
    for finding in findings:
        if not applies(finding, aggressive):
            continue
        parts.append(text[pos : finding.start])
        parts.append(finding.american)
        pos = finding.end
    parts.append(text[pos:])
    return "".join(parts)


def applies(finding: Finding, aggressive: bool) -> bool:
    """True when --write should rewrite this finding."""
    if finding.rule == "proper-noun":
        return False
    if finding.ambiguous:
        return aggressive
    return True


def convert_text(text: str, aggressive: bool = False, disabled: frozenset = frozenset()) -> str:
    """Convert a whole document. The pure function the selftest drives."""
    findings, _ = scan_text(text, "<text>", disabled)
    return apply_findings(text, findings, aggressive)


# ==========================================================================
# Part 5 -- renderers
# ==========================================================================


def format_finding(finding: Finding) -> str:
    """`path:line:col: british -> american  (rule: name)`."""
    head = "%s:%d:%d: %s -> %s  (rule: %s" % (
        finding.path,
        finding.line,
        finding.col,
        finding.british,
        finding.american,
        finding.rule,
    )
    if finding.reason:
        head += "; " + finding.reason
    return head + ")"


def finding_as_dict(finding: Finding) -> dict:
    return {
        "line": finding.line,
        "col": finding.col,
        "british": finding.british,
        "american": finding.american,
        "rule": finding.rule,
        "ambiguous": finding.ambiguous,
        "in_blockquote": finding.in_blockquote,
        "reason": finding.reason,
        "context": finding.context,
    }


def restrict_stats(totals: Stats, per_file: list) -> Stats:
    """Recount the finding counters over a filtered view of the findings.

    The file-level counters are carried over unchanged: they describe the scan,
    not the report. Without this, `--no-ambiguous --json` shows a `stats` block
    that counts findings the payload does not list.
    """
    trimmed = Stats()
    trimmed.files = totals.files
    trimmed.skipped_files = totals.skipped_files
    trimmed.identifier_skip = totals.identifier_skip
    for _, findings in per_file:
        for finding in findings:
            trimmed.record(finding)
    return trimmed


def render_text_report(per_file: list, aggressive: bool = False) -> list[str]:
    """The human report: certain findings first, then the flagged tier."""
    lines: list[str] = []
    certain = []
    flagged = []
    for _, findings in per_file:
        for finding in findings:
            (flagged if finding.ambiguous else certain).append(finding)
    for finding in certain:
        lines.append(format_finding(finding))
    if flagged:
        if certain:
            lines.append("")
        applied = [f for f in flagged if applies(f, aggressive)]
        if aggressive and applied:
            lines.append("-- flagged; %d of these are applied under --aggressive --" % len(applied))
        else:
            lines.append("-- flagged, not applied without --aggressive --")
        for finding in flagged:
            lines.append(format_finding(finding))
    return lines


def render_json_report(per_file: list, stats: Stats) -> str:
    payload = {
        "version": 1,
        "files": [
            {"path": path, "findings": [finding_as_dict(f) for f in findings]}
            for path, findings in per_file
        ],
        "stats": stats.as_dict(),
    }
    return json.dumps(payload, indent=2, sort_keys=False)


def render_stats(stats: Stats) -> list[str]:
    data = stats.as_dict()
    lines = ["", "stats:"]
    for key in ("files", "skipped_files", "findings", "convertible", "ambiguous", "proper_noun", "identifier_skip"):
        lines.append("  %-16s %d" % (key, data[key]))
    if data["by_rule"]:
        lines.append("  by_rule:")
        for rule, count in data["by_rule"].items():
            lines.append("    %-14s %d" % (rule, count))
    return lines


def render_diff(path: str, before: str, after: str) -> list[str]:
    """A unified diff, or an empty list when nothing changed."""
    if before == after:
        return []
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile="a/" + path,
        tofile="b/" + path,
        n=2,
    )
    lines = []
    for line in diff:
        if line.endswith("\n"):
            lines.append(line[:-1])
            continue
        # difflib never emits this marker. Without it the patch claims the file
        # ends in a newline, and both `git apply` and `patch` reject the hunk.
        lines.append(line)
        lines.append("\\ No newline at end of file")
    return lines


def render_diff_json(payload: list, stats: Stats) -> str:
    files = [{"path": path, "diff": "\n".join(lines)} for path, lines in payload]
    return json.dumps(
        {"version": 1, "files": files, "stats": stats.as_dict()}, indent=2, sort_keys=False
    )


def render_write_json(summaries: list, stats: Stats) -> str:
    files = [
        {
            "path": path,
            "applied": applied,
            "flagged": len(findings) - applied,
            "written": written,
            "findings": [finding_as_dict(f) for f in findings],
        }
        for path, findings, applied, written in summaries
    ]
    return json.dumps(
        {"version": 1, "files": files, "stats": stats.as_dict()}, indent=2, sort_keys=False
    )


# ==========================================================================
# Part 6 -- file IO and the CLI
# ==========================================================================


class UsageError(Exception):
    """A bad invocation or an unreadable file. Always exit 2."""


def read_text(path: Path) -> str:
    """Read a file without translating line endings."""
    if path.is_dir():
        raise UsageError("%s: is a directory (pass file paths, not directories)" % path)
    try:
        with open(path, "r", encoding="utf-8", newline="") as handle:
            return handle.read()
    except FileNotFoundError:
        raise UsageError("%s: no such file" % path) from None
    except IsADirectoryError:
        raise UsageError("%s: is a directory" % path) from None
    except UnicodeDecodeError:
        raise UsageError("%s: not valid UTF-8" % path) from None
    except OSError as exc:
        raise UsageError("%s: %s" % (path, exc.strerror)) from None


def write_text(path: Path, text: str) -> None:
    """Write a file without translating line endings."""
    try:
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
    except OSError as exc:
        raise UsageError("%s: %s" % (path, exc.strerror)) from None


def merge_stats(target: Stats, source: Stats) -> None:
    target.files += source.files
    target.skipped_files += source.skipped_files
    target.findings += source.findings
    target.convertible += source.convertible
    target.ambiguous += source.ambiguous
    target.proper_noun += source.proper_noun
    target.identifier_skip += source.identifier_skip
    for rule, count in source.by_rule.items():
        target.by_rule[rule] = target.by_rule.get(rule, 0) + count


def _load_files(paths: list) -> tuple:
    """Read every path up front, collecting the ones that fail.

    Reading everything before anything is scanned or written is what makes the
    error policy consistent: one missing path can neither discard the findings
    of the files that were readable, nor leave half a tree rewritten.
    """
    loaded = []
    errors = []
    for raw in paths:
        try:
            loaded.append((raw, read_text(Path(raw))))
        except UsageError as exc:
            errors.append(str(exc))
    return loaded, errors


def _report_errors(errors: list) -> int:
    for message in errors:
        print("%s: %s" % (PROGRAM, message), file=sys.stderr)
    return EXIT_ERROR if errors else EXIT_OK


def _warn_directives(loaded: list) -> None:
    for path, text in loaded:
        for warning in directive_warnings(text, path):
            print("%s: %s" % (PROGRAM, warning), file=sys.stderr)


def _scan_loaded(loaded: list, disabled: frozenset) -> tuple:
    per_file = []
    totals = Stats()
    for raw, text in loaded:
        findings, stats = scan_text(text, raw, disabled)
        merge_stats(totals, stats)
        per_file.append((raw, findings))
    return per_file, totals


def run_check(args: argparse.Namespace, disabled: frozenset) -> int:
    loaded, errors = _load_files(args.files)
    _warn_directives(loaded)
    per_file, totals = _scan_loaded(loaded, disabled)
    if args.no_ambiguous:
        per_file = [(p, [f for f in fs if not f.ambiguous]) for p, fs in per_file]
        totals = restrict_stats(totals, per_file)
    if not args.quiet:
        if args.json:
            print(render_json_report(per_file, totals))
        else:
            for line in render_text_report(per_file, args.aggressive):
                print(line)
            if args.stats:
                for line in render_stats(totals):
                    print(line)
    if errors:
        return _report_errors(errors)
    return EXIT_FINDINGS if totals.findings else EXIT_OK


def run_diff(args: argparse.Namespace, disabled: frozenset) -> int:
    loaded, errors = _load_files(args.files)
    _warn_directives(loaded)
    totals = Stats()
    payload = []
    for raw, text in loaded:
        findings, stats = scan_text(text, raw, disabled)
        merge_stats(totals, stats)
        converted = apply_findings(text, findings, args.aggressive)
        payload.append((raw, render_diff(raw, text, converted)))
    if not args.quiet:
        if args.json:
            print(render_diff_json(payload, totals))
        else:
            for _, lines in payload:
                for line in lines:
                    print(line)
            if args.stats:
                for line in render_stats(totals):
                    print(line)
    return _report_errors(errors)


def run_write(args: argparse.Namespace, disabled: frozenset) -> int:
    loaded, errors = _load_files(args.files)
    _warn_directives(loaded)
    status = _report_errors(errors)
    totals = Stats()
    summaries = []
    for raw, text in loaded:
        # A file is never rewritten unless masking it is provably lossless.
        if not round_trips(text):
            print("%s: %s: refusing to write, mask round-trip failed" % (PROGRAM, raw), file=sys.stderr)
            status = EXIT_ERROR
            continue
        findings, stats = scan_text(text, raw, disabled)
        merge_stats(totals, stats)
        converted = apply_findings(text, findings, args.aggressive)
        applied = sum(1 for f in findings if applies(f, args.aggressive))
        written = converted != text
        if written:
            try:
                write_text(Path(raw), converted)
            except UsageError as exc:
                print("%s: %s" % (PROGRAM, exc), file=sys.stderr)
                status = EXIT_ERROR
                continue
        summaries.append((raw, findings, applied, written))
    if not args.quiet:
        if args.json:
            print(render_write_json(summaries, totals))
        else:
            for raw, findings, applied, _written in summaries:
                print("%s: %d change(s) applied, %d flagged" % (raw, applied, len(findings) - applied))
            # The flagged tier is the whole point of the second pass, so name
            # it here rather than making the caller re-run --check.
            leftover = [f for _, fs, _, _ in summaries for f in fs if not applies(f, args.aggressive)]
            if leftover:
                print("")
                print("-- flagged, left for review --")
                for finding in leftover:
                    print(format_finding(finding))
            if args.stats:
                for line in render_stats(totals):
                    print(line)
    return status


def run_stdin(args: argparse.Namespace, disabled: frozenset) -> int:
    raw = sys.stdin.buffer.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise UsageError("stdin: not valid UTF-8") from None
    for warning in directive_warnings(text, "<stdin>"):
        print("%s: %s" % (PROGRAM, warning), file=sys.stderr)
    findings, stats = scan_text(text, "<stdin>", disabled)
    converted = apply_findings(text, findings, args.aggressive)
    sys.stdout.buffer.write(converted.encode("utf-8"))
    if args.stats and not args.quiet:
        # stdout carries the converted document, so the counters go to stderr.
        for line in render_stats(stats):
            print(line, file=sys.stderr)
    return EXIT_OK


EPILOG = """\
escape hatches, written as HTML comments in the document (engb: and gb2us:
are synonyms, and the separator in a two-word name is free):
  <!-- engb:off --> ... <!-- engb:on -->   skip the enclosed span
  <!-- engb:ignore-line -->                skip the line it sits on
  <!-- engb:ignore-next -->                skip the next non-blank line
  <!-- engb:skip-file -->                  skip the file (first 20 lines)
  <!-- verbatim -->                        skip the next block, no closer needed
Wrap a British-to-American conversion table in engb:off: a table that spells
both forms on purpose is otherwise flattened into two American columns.

Exit codes: 0 clean, 1 findings present (--check), 2 usage or IO error.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROGRAM,
        description="Convert British English spellings to American English in Markdown.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report findings, never write (default)")
    mode.add_argument("--diff", action="store_true", help="print a unified diff, never write")
    mode.add_argument("--write", action="store_true", help="rewrite the files in place")
    mode.add_argument("--stdin", action="store_true", help="filter stdin to stdout")
    mode.add_argument("--selftest", action="store_true", help="run the built-in assertions")
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument(
        "--json",
        action="store_true",
        help="machine-readable output for --check, --diff and --write (not --stdin)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="print counters (on stderr under --stdin, so stdout stays the document)",
    )
    parser.add_argument(
        "--aggressive",
        action="store_true",
        help="also apply the ambiguous tier (never the proper-noun tier)",
    )
    parser.add_argument(
        "--no-ambiguous",
        action="store_true",
        help="omit the flagged tier from --check output and from the exit code",
    )
    parser.add_argument(
        "--no-rule",
        action="append",
        default=[],
        metavar="NAME",
        help="disable a rule family; NAME is any label printed in a finding (%s)"
        % ", ".join(RULE_NAMES + TIER_NAMES),
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="print nothing on stdout; exit code only"
    )
    parser.add_argument("files", nargs="*", metavar="FILE", help="file paths, no globbing")
    return parser


def main(argv: "list[str] | None" = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    unknown = [rule for rule in args.no_rule if rule not in RULE_NAMES + TIER_NAMES]
    if unknown:
        print("%s: unknown rule(s): %s" % (PROGRAM, ", ".join(unknown)), file=sys.stderr)
        return EXIT_ERROR
    disabled = frozenset(args.no_rule)

    if args.selftest:
        return run_selftest_cli()

    try:
        if args.stdin:
            if args.files:
                raise UsageError("--stdin takes no FILE arguments")
            if args.json:
                raise UsageError("--json is not available with --stdin (stdout is the document)")
            return run_stdin(args, disabled)
        if not args.files:
            raise UsageError("no files given (see --help)")
        if args.write:
            return run_write(args, disabled)
        if args.diff:
            return run_diff(args, disabled)
        return run_check(args, disabled)
    except UsageError as exc:
        print("%s: %s" % (PROGRAM, exc), file=sys.stderr)
        return EXIT_ERROR


# ==========================================================================
# Part 7 -- selftest
#
# Every assertion below defends a named behaviour. The corpus is the
# specification: if a rule family, an exception list, a protected region, or a
# case pattern is not represented here, it is not covered.
# ==========================================================================

# Conversions the converter must make. One assertion each, run over a bare
# one-word document so no context guard can interfere.
CONVERT_CASES = """
colour color
colours colors
coloured colored
colouring coloring
colourful colorful
colourless colorless
colouration coloration
colourway colorway
discoloured discolored
behaviour behavior
behavioural behavioral
neighbourhood neighborhood
labourer laborer
vapourware vaporware
favourite favorite
unfavourable unfavorable
honourable honorable
humourless humorless
armoury armory
saviour savior
endeavour endeavor
rumours rumors
centre center
centres centers
centred centered
centring centering
centrepiece centerpiece
epicentre epicenter
metre meter
kilometre kilometer
millimetre millimeter
litre liter
fibre fiber
fibreglass fiberglass
sabre saber
sombre somber
theatre theater
lustre luster
mitred mitered
manoeuvre maneuver
manoeuvring maneuvering
manoeuvrability maneuverability
organise organize
organisation organization
organisational organizational
organiser organizer
summarise summarize
publicise publicize
minimise minimize
dramatise dramatize
crystallise crystallize
baptise baptize
containerise containerize
moisturise moisturize
aggrandisement aggrandizement
realisable realizable
recognise recognize
unrealisable unrealizable
analyse analyze
analysed analyzed
analysing analyzing
analyser analyzer
paralyse paralyze
catalyse catalyze
breathalyse breathalyze
haemolyse hemolyze
catalogue catalog
cataloguing cataloging
catalogued cataloged
cataloguer cataloger
analogue analog
encyclopaedia encyclopedia
foetus fetus
oestrogen estrogen
anaemia anemia
diarrhoea diarrhea
haemoglobin hemoglobin
paediatric pediatric
mediaeval medieval
oesophagus esophagus
anaesthetic anesthetic
gynaecology gynecology
orthopaedic orthopedic
defence defense
offence offense
pretence pretense
licence license
licencee licensee
practise practice
practised practiced
practising practicing
premiss premise
travelled traveled
travelling traveling
traveller traveler
cancelled canceled
cancelling canceling
labelled labeled
modelling modeling
signalling signaling
marshalling marshaling
unmarshalling unmarshaling
tunnelling tunneling
levelling leveling
totalling totaling
fuelled fueled
dialled dialed
counsellor counselor
marvellous marvelous
jewellery jewelry
libellous libelous
panellist panelist
woollen woolen
parallelled paralleled
parallelling paralleling
enrol enroll
enrolment enrollment
fulfil fulfill
fulfilment fulfillment
instalment installment
instil instill
distil distill
enthral enthrall
appal appall
instal install
skilful skillful
wilful willful
programme program
programmes programs
gramme gram
kilogramme kilogram
judgement judgment
judgemental judgmental
acknowledgement acknowledgment
abridgement abridgment
colourise colorize
colourisation colorization
colourises colorizes
vapourise vaporize
desulphurisation desulfurization
sulphurise sulfurize
sulphur sulfur
anaesthetise anesthetize
plough plow
ploughed plowed
humourous humorous
vigourous vigorous
labourious laborious
honourary honorary
glamourous glamorous
glamourise glamorize
focussed focused
focussing focusing
biassed biased
benefitted benefited
targetted targeted
combatted combated
aluminium aluminum
caesium cesium
tyres tires
aeroplane airplane
moustache mustache
pyjamas pajamas
storeys stories
sceptical skeptical
artefact artifact
connexion connection
furore furor
cheque check
kerb curb
mould mold
smoulder smolder
cosy cozy
orientated oriented
recognisably recognizably
recognisance recognizance
cognisance cognizance
cognisant cognizant
organisationally organizationally
centrefolds centerfolds
meagreness meagerness
moulders molders
mouldering moldering
gaolers jailers
gaoling jailing
kerbed curbed
kerbing curbing
chequer checker
chequers checkers
chequerboard checkerboard
chequing checking
draughtsmen draftsmen
draughted drafted
draughting drafting
updraught updraft
downdraught downdraft
greyscale grayscale
multistorey multistory
prejudgement prejudgment
misjudgement misjudgment
reprogramme reprogram
reprogrammes reprograms
psychoanalyse psychoanalyze
psychoanalysed psychoanalyzed
carburetter carburetor
disorientated disoriented
disorientating disorienting
multicolour multicolor
multicoloured multicolored
watercolour watercolor
watercolours watercolors
tricolour tricolor
varicoloured varicolored
clangour clangor
lacklustre lackluster
aetiology etiology
aetiological etiological
toxaemia toxemia
bacteraemia bacteremia
gonorrhoea gonorrhea
pyorrhoea pyorrhea
lymphoedema lymphedema
foetid fetid
aerofoil airfoil
trialled trialed
trialling trialing
empanelled empaneled
impanelling impaneling
enamelled enameled
funnelled funneled
gambolled gamboled
trammelled trammeled
snivelled sniveled
bushelled busheled
apparelled appareled
cypher cipher
cyphers ciphers
liquorice licorice
almanack almanac
baulked balked
eyrie aerie
rouble ruble
waggon wagon
nett net
groyne groin
callisthenics calisthenics
behoves behooves
dependant dependent
enquire inquire
enquiry inquiry
enquiries inquiries
sizeable sizable
queueing queuing
nought naught
maths math
whilst while
amongst among
flautist flutist
callisthenic calisthenic
draughtier draftier
draughtiness draftiness
mouldier moldier
mouldiness moldiness
"""

# Words the converter must leave exactly as they are. One assertion each.
UNCHANGED_CASES = """
color center organize analyze catalog defense license traveled canceled
enroll fulfill program judgment fiber meter liter theater specter
advertise advertised advertising advertisement advertisements
advise advised advising advisable advisability adviser
apprise arise arising rise rising sunrise
chastise circumcise comprise comprised comprising
compromise compromised compromising demise despise despised
devise devised disguise disguised enterprise enterprises
excise exercise exercised exercising exercisable expertise
franchise franchised franchising guise improvise improvising
improvisation improvisations incise merchandise merchandising
mortise paradise precise concise premise promise promising
reprise revise revised revising supervise supervising surmise
surprise surprised surprising surprisingly televise televised
treatise valise anise cerise wise likewise otherwise clockwise
counterclockwise crosswise lengthwise edgewise streetwise
raise praise appraise braise liaise malaise chaise mayonnaise
noise poise turquoise tortoise porpoise bruise cruise crises
size prize seize capsize
geyser geysers lyse lysed lysing analysis paralysis catalysis
dialysis analyst analysts analytic analytical
are were here there where more before score store core bore ignore
genre genres acre acres acreage ogre ogres cadre cadres macabre
mediocre mediocrity massacre lucre nacre euchre chancre
padre timbre timbres oeuvre libre
four hour your tour pour sour flour scour devour contour velour
detour amour paramour troubadour dour our glamour glamours
humorous laborious vigorous rigorous odorous clamorous honorary
honorific laboratory
controlled controlling controller controllers uncontrolled
patrolled patrolling extolled compelled compelling expelled
propelled propeller repelled dispelled rebelled excelled annulled
enrolled enrolling enrollment installed installing installer
installation fulfilled fulfilling instilled distilled distillery
appalled appalling enthralled impelled
paralleled paralleling parallel parallelism
cancellation cancellations constellation medallion metallic
programmed programming programmer programmers programmable
spelled smelled swelled dwelled polled polling rolled rolling
scrolled scrolling stalled calling filling killing billing pulling
milling drilling skilled unskilled
worshipped kidnapped formatted committed omitted
shoulder boulder
aesthetic aesthetics aesthete archaeology archaeological aegis
amoeba amoebae phoenix onomatopoeia subpoena maestro paella sundae
algae formulae vertebrae larvae antennae daemon daemons
aerial aerobic aerosol aerospace aeronautics
coefficient coerce coexist coeval poem poet does shoe toe goes
monologue prologue epilogue travelogue demagogue synagogue
ideologue pedagogue rogue vogue brogue
greyhound greyhounds libre metric theatrical fibrous spectrum
calibrate centrifugal geometric symmetric parameter diameter
irises trellises trellised trellising metropolises megalopolises
pelvises mantises chrysalises clematises amaryllises ibises
proboscises portcullises epidermises epiglottises glottises penises
clitorises cannabises finises verdigrises acropolises necropolises
imprecise imprecisely imprecision inadvisable inadvisability
ultraprecise semiprecise hyperprecise superprecise multipremise
interprecise counterprecise disadvise misadvise unwise
exorcise exorcised exorcising exorcism Denise Elise Cochise
nuisance renaissance reconnaissance croissant puissance
"""

# The ambiguous tier: reported, never applied without --aggressive.
AMBIGUOUS_CASES = """
analyses paralyses catalyses dialyses hydrolyses electrolyses
disc discs dialogue dialogues draughts storeyed spelt smelt burnt
dreamt leapt prise prised vice calibre greylist greylisting
homologue tonne autolyse speciality
calibres specialities spoilt unlearnt prises prising
"""

# Full-document guard assertions: (document, expected document).
GUARD_CASES = (
    ("`colour`", "`colour`"),
    ("``a ` and colour``", "``a ` and colour``"),
    ("```\ncolour\n```\n", "```\ncolour\n```\n"),
    ("~~~yaml\ncolour: red\n~~~\n", "~~~yaml\ncolour: red\n~~~\n"),
    ("Text.\n\n    colour = 1\n", "Text.\n\n    colour = 1\n"),
    ("- item\n\n    colour continues\n", "- item\n\n    color continues\n"),
    ('<span data-colour="x">colour</span>', '<span data-colour="x">color</span>'),
    ("<pre>colour</pre>", "<pre>colour</pre>"),
    ("See https://example.com/colour now", "See https://example.com/colour now"),
    ("<https://x.uk/colour>", "<https://x.uk/colour>"),
    ("[colour guide](/colour-guide)", "[color guide](/colour-guide)"),
    ("[a][colour-ref]", "[a][colour-ref]"),
    ("[colour-ref]: /x/colour\n", "[colour-ref]: /x/colour\n"),
    ("Pass --colour-output here", "Pass --colour-output here"),
    ("Pass --no-colour here", "Pass --no-colour here"),
    ("A ColourMap value", "A ColourMap value"),
    ("A colourMap value", "A colourMap value"),
    ("A COLOur value", "A COLOur value"),
    ("The colour_scheme key", "The colour_scheme key"),
    ("The colour.value key", "The colour.value key"),
    ("The colour/path key", "The colour/path key"),
    ("The colour2 key", "The colour2 key"),
    ("The X-Colour-Scheme header", "The X-Colour-Scheme header"),
    ("A CentreOS box", "A CentreOS box"),
    ("A behaviour-driven flow", "A behavior-driven flow"),
    ("The data centre here", "The data center here"),
    ("A two-storey block", "A two-story block"),
    ("Fibre Channel works", "Fibre Channel works"),
    ("fibre channel works", "fibre channel works"),
    ("The fibre optics", "The fiber optics"),
    ("Spectre and Meltdown", "Spectre and Meltdown"),
    ("Earl Grey tea", "Earl Grey tea"),
    ("the grey box", "the gray box"),
    ("Encyclopaedia Britannica", "Encyclopaedia Britannica"),
    ("Open Government Licence", "Open Government Licence"),
    ("## Licence\n", "## License\n"),
    ("Erasmus Programme", "Erasmus Programme"),
    ("the programme runs nightly", "the program runs nightly"),
    ("a compact disc drive", "a compact disc drive"),
    ("a hard disc drive", "a hard disk drive"),
    ("a dialogue box here", "a dialog box here"),
    ("the dialogue between teams", "the dialogue between teams"),
    ("ten per cent", "ten percent"),
    (
        "---\nname: colour-tool\ndescription: A colour tool\n---\n",
        "---\nname: colour-tool\ndescription: A color tool\n---\n",
    ),
    ("<!-- engb:off -->colour<!-- engb:on -->", "<!-- engb:off -->colour<!-- engb:on -->"),
    ("<!-- engb:skip-file -->\ncolour\n", "<!-- engb:skip-file -->\ncolour\n"),
    ("colour <!-- engb:ignore-line -->", "colour <!-- engb:ignore-line -->"),
    ("<!-- engb:ignore-next -->\ncolour\n", "<!-- engb:ignore-next -->\ncolour\n"),
    ("> a quoted colour\n", "> a quoted color\n"),
    ("the organisation's rules", "the organization's rules"),
    ("Earl\nGrey tea", "Earl\nGrey tea"),
    ("Erasmus\nProgramme runs", "Erasmus\nProgramme runs"),
    ("Fibre\nChannel works", "Fibre\nChannel works"),
    ("A colour.\nBehaviour follows.", "A color.\nBehavior follows."),
    ("A Colour\n\nGuide here", "A Color\n\nGuide here"),
    ("don't touch the colour", "don't touch the color"),
    ("COLOUR and Colour and colour", "COLOR and Color and color"),
    ("Behaviour is fine.", "Behavior is fine."),
    ("The Colour Guide", "The Colour Guide"),
    ("`colour` and colour", "`colour` and color"),
    ("colour, colour. colour!", "color, color. color!"),
    ("| colour | code |\n|---|---|\n", "| color | code |\n|---|---|\n"),
    ("**colour** and _colour_", "**color** and _color_"),
    ("colour\r\nbehaviour\r\n", "color\r\nbehavior\r\n"),
    ("no trailing newline colour", "no trailing newline color"),
    # inline literal HTML: `<pre>` is not the only element that holds tokens
    ("<code>colour</code>", "<code>colour</code>"),
    ("Key <code>colour</code> here", "Key <code>colour</code> here"),
    ('<code class="x">metre</code>', '<code class="x">metre</code>'),
    ("<samp>colour</samp>", "<samp>colour</samp>"),
    ("<var>colour</var>", "<var>colour</var>"),
    ("<kbd>colour</kbd>", "<kbd>colour</kbd>"),
    ("<tt>colour</tt>", "<tt>colour</tt>"),
    ("<pre><code>colour</code></pre>", "<pre><code>colour</code></pre>"),
    # shortcut and collapsed reference links are their own link target
    ("See [colour] now.\n\n[colour]: /c\n", "See [colour] now.\n\n[colour]: /c\n"),
    ("See [colour][] now.\n\n[colour]: /c\n", "See [colour][] now.\n\n[colour]: /c\n"),
    ("See [COLOUR] now.\n\n[colour]: /c\n", "See [COLOUR] now.\n\n[colour]: /c\n"),
    ("See [text][colour].\n\n[colour]: /c\n", "See [text][colour].\n\n[colour]: /c\n"),
    ("A [colour] with no definition", "A [color] with no definition"),
    ("[colour](/x) here\n\n[colour]: /c\n", "[color](/x) here\n\n[colour]: /c\n"),
    # template placeholders are identifiers, whatever the brace style
    ("Use {colour} here", "Use {colour} here"),
    ("Use {colour!r} here", "Use {colour!r} here"),
    ("Use {colour:>8} here", "Use {colour:>8} here"),
    ("Use %(colour)s here", "Use %(colour)s here"),
    ("Use %(colour)-8.2f here", "Use %(colour)-8.2f here"),
    ("Use {% if colour %} here", "Use {% if colour %} here"),
    ("Use {# colour #} here", "Use {# colour #} here"),
    ("Use {{colour}} here", "Use {{colour}} here"),
    ("Use ${colour} here", "Use ${colour} here"),
    ("An &colour; entity", "An &colour; entity"),
    ("An &amp; and a colour", "An &amp; and a color"),
    # names: ALL CAPS, and runs held together by a lowercase connector
    ("the MITRE ATT&CK framework", "the MITRE ATT&CK framework"),
    ("a MITRE joint", "a MITRE joint"),
    ("THE DEFENCE BUDGET", "THE DEFENSE BUDGET"),
    ("COLOUR AND BEHAVIOUR", "COLOR AND BEHAVIOR"),
    ("the Ministry of Defence", "the Ministry of Defence"),
    ("the Centre for Disease Control", "the Centre for Disease Control"),
    ("the Defence Industries Association", "the Defence Industries Association"),
    ("the Labour party", "the Labour party"),
    ("the defence budget", "the defense budget"),
    ("Defence spending rose", "Defense spending rose"),
    # a token carrying a non-ASCII letter is not an English word
    ("Unicode colour\u00e9 here", "Unicode colour\u00e9 here"),
    ("Unicode \u00e9colour here", "Unicode \u00e9colour here"),
    ("Caf\u00e9 and colour", "Caf\u00e9 and color"),
    # directive spellings a writer is likely to guess
    ("<!-- engb:verbatim -->\ncolour\n", "<!-- engb:verbatim -->\ncolour\n"),
    ("colour <!-- engb:ignoreline -->", "colour <!-- engb:ignoreline -->"),
    ("<!-- engb:ignore_next -->\ncolour\n", "<!-- engb:ignore_next -->\ncolour\n"),
    ("<!-- engb:skipfile -->\ncolour\n", "<!-- engb:skipfile -->\ncolour\n"),
)


def _selftest_words(source: str) -> list:
    return [w for line in source.strip().splitlines() for w in line.split()]


class _CaptureStdout(io.StringIO):
    """A stdout stand-in that also offers the `.buffer` --stdin writes to."""

    def __init__(self) -> None:
        super().__init__()
        self.buffer = io.BytesIO()


class _FakeStdin:
    """Just enough of sys.stdin for run_stdin()."""

    def __init__(self, data: bytes) -> None:
        self.buffer = io.BytesIO(data)


def _captured_main(argv: list) -> tuple:
    """Run main() with both streams captured. Returns (exit code, stdout)."""
    out = _CaptureStdout()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue()


def _silent_main(argv: list) -> int:
    """Run main() with both streams captured, so a selftest stays quiet."""
    return _captured_main(argv)[0]


def _stdin_main(data: bytes, argv: list) -> tuple:
    """Run the CLI over `data` on stdin. Returns (exit code, stdout bytes)."""
    saved = sys.stdin
    sys.stdin = _FakeStdin(data)
    out = _CaptureStdout()
    err = io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv)
    finally:
        sys.stdin = saved
    return code, out.buffer.getvalue()


def _check(failures: list, label: str, got, want) -> None:
    if got != want:
        failures.append("%s: got %r, want %r" % (label, got, want))


def run_selftest() -> tuple[list, int]:
    """Run every assertion. Returns (failures, assertion count)."""
    failures: list = []
    count = 0

    # --- structural invariants over the tables ---------------------------
    invariants = (
        ("OUR_STEMS vs OUR_NEVER", set(OUR_STEMS) & OUR_NEVER),
        ("RE_STEMS vs RE_NEVER", set(RE_STEMS) & RE_NEVER),
        ("OGUE_WORDS vs OGUE_NEVER", set(OGUE_WORDS) & OGUE_NEVER),
        ("AE_OE_WORDS vs AE_OE_NEVER", set(AE_OE_WORDS) & AE_OE_NEVER),
        ("CE_SE_WORDS vs CE_SE_NEVER", set(CE_SE_WORDS) & CE_SE_NEVER),
        ("DOUBLE_L_STEMS vs DOUBLE_L_NEVER", DOUBLE_L_STEMS & DOUBLE_L_NEVER),
        ("SINGLE_L_WORDS vs DOUBLE_L_STEMS", set(SINGLE_L_WORDS) & DOUBLE_L_STEMS),
        ("PROGRAMME_WORDS vs IRREGULAR_WORDS", set(PROGRAMME_WORDS) & set(IRREGULAR_WORDS)),
        ("AMBIGUOUS vs IRREGULAR_WORDS", set(AMBIGUOUS) & set(IRREGULAR_WORDS)),
        ("AMBIGUOUS vs OGUE_WORDS", set(AMBIGUOUS) & set(OGUE_WORDS)),
    )
    for label, overlap in invariants:
        count += 1
        _check(failures, "disjoint " + label, sorted(overlap), [])

    for table, _rule in EXACT_TABLES:
        count += 1
        identity = sorted(k for k, v in table.items() if k == v)
        _check(failures, "no identity entries", identity, [])

    count += 1
    _check(failures, "rule names are unique", len(set(RULE_NAMES)), len(RULE_NAMES))

    # --- rule families ---------------------------------------------------
    pairs = _selftest_words(CONVERT_CASES)
    for i in range(0, len(pairs), 2):
        british, american = pairs[i], pairs[i + 1]
        count += 1
        _check(failures, "convert " + british, convert_text(british), american)
        # Fixed point: the output must never convert again.
        count += 1
        _check(failures, "fixed point " + american, convert_text(american), american)

    for word in _selftest_words(UNCHANGED_CASES):
        count += 1
        _check(failures, "unchanged " + word, convert_text(word), word)

    # --- the ambiguous tier ----------------------------------------------
    for word in _selftest_words(AMBIGUOUS_CASES):
        findings, _ = scan_text(word, "<t>")
        count += 1
        _check(failures, "flagged " + word, [f.ambiguous for f in findings], [True])
        count += 1
        _check(failures, "not written " + word, convert_text(word), word)
        count += 1
        _check(
            failures,
            "aggressive writes " + word,
            convert_text(word, aggressive=True) != word,
            True,
        )

    # --- guards ----------------------------------------------------------
    for document, expected in GUARD_CASES:
        count += 1
        _check(failures, "guard %r" % document[:40], convert_text(document), expected)

    # --- case preservation -----------------------------------------------
    for token, expected in (("colour", "color"), ("Colour", "Color"), ("COLOUR", "COLOR")):
        count += 1
        _check(failures, "case " + token, convert_text(token), expected)
    for token in ("ColourMap", "colourMap", "COLOur"):
        count += 1
        _check(failures, "identifier case " + token, case_pattern(token), None)

    # --- idempotence, round trip, line endings ---------------------------
    documents = [doc for doc, _ in GUARD_CASES] + [
        "colour\n\n```\ncolour\n```\n\n> colour\n",
        "---\ntitle: A colour guide\nname: colour\n---\n\nThe colour is fine.\n",
        "",
        "\n",
        "   ",
        "```",
        "`",
        "---\n",
        "[a]: b\n",
        MASK_OPEN + "0" + MASK_CLOSE,
    ]
    for document in documents:
        count += 1
        _check(failures, "round trip %r" % document[:30], round_trips(document), True)
        once = convert_text(document)
        count += 1
        _check(failures, "idempotent %r" % document[:30], convert_text(once), once)
        count += 1
        _check(
            failures,
            "trailing newline %r" % document[:30],
            once.endswith("\n"),
            document.endswith("\n"),
        )
        count += 1
        _check(failures, "CR count %r" % document[:30], once.count("\r"), document.count("\r"))
        count += 1
        _check(failures, "line count %r" % document[:30], once.count("\n"), document.count("\n"))

    # --- findings shape and exit codes -----------------------------------
    findings, stats = scan_text("The colour is here.\n", "docs/x.md")
    count += 1
    _check(failures, "one finding", len(findings), 1)
    count += 1
    _check(failures, "finding format", format_finding(findings[0]), "docs/x.md:1:5: colour -> color  (rule: our-or)")
    count += 1
    _check(failures, "finding line", findings[0].line, 1)
    count += 1
    _check(failures, "finding col", findings[0].col, 5)
    count += 1
    _check(failures, "stats convertible", stats.convertible, 1)
    count += 1
    _check(failures, "stats by rule", stats.by_rule, {"our-or": 1})
    count += 1
    _check(failures, "json parses", json.loads(render_json_report([("docs/x.md", findings)], stats))["version"], 1)

    quoted, _ = scan_text("> a quoted colour\n", "<t>")
    count += 1
    _check(failures, "blockquote flag", [f.in_blockquote for f in quoted], [True])

    proper, _ = scan_text("Earl Grey tea", "<t>")
    count += 1
    _check(failures, "proper noun rule", [f.rule for f in proper], ["proper-noun"])
    count += 1
    _check(failures, "proper noun not applied", [applies(f, True) for f in proper], [False])

    clean, _ = scan_text("The color is here.\n", "<t>")
    count += 1
    _check(failures, "clean file has no findings", clean, [])

    # Exit codes for the pure-function paths.
    count += 1
    _check(failures, "exit clean", _silent_main(["--check", "--quiet", __file__]) in (0, 1), True)
    count += 1
    _check(failures, "exit unknown rule", _silent_main(["--check", "--no-rule", "nope", __file__]), EXIT_ERROR)
    count += 1
    _check(failures, "exit missing file", _silent_main(["--check", "/nonexistent/xyz.md"]), EXIT_ERROR)
    count += 1
    _check(failures, "exit directory", _silent_main(["--check", str(Path(__file__).parent)]), EXIT_ERROR)
    count += 1
    _check(failures, "exit stdin with files", _silent_main(["--stdin", __file__]), EXIT_ERROR)
    count += 1
    _check(failures, "exit no files", _silent_main([]), EXIT_ERROR)

    # --- rule groups can be disabled -------------------------------------
    count += 1
    _check(failures, "no-rule si-units", convert_text("metre", disabled=frozenset({"si-units"})), "metre")
    count += 1
    _check(failures, "no-rule keeps our-or", convert_text("colour", disabled=frozenset({"si-units"})), "color")
    count += 1
    _check(failures, "no-rule iupac", convert_text("aluminium", disabled=frozenset({"iupac"})), "aluminium")

    # --- diff renderer ----------------------------------------------------
    diff = render_diff("x.md", "colour\n", "color\n")
    count += 1
    _check(failures, "diff has a header", diff[0], "--- a/x.md")
    count += 1
    _check(failures, "diff has no output when equal", render_diff("x.md", "a\n", "a\n"), [])
    # A file with no final newline needs the marker on both sides, or no
    # applier will take the patch.
    nonl = render_diff("x.md", "a\nThe colour", "a\nThe color")
    count += 1
    _check(failures, "diff marks a missing final newline", nonl.count("\\ No newline at end of file"), 2)
    count += 1
    _check(failures, "diff marker follows its line", nonl[-2:], ["+The color", "\\ No newline at end of file"])
    count += 1
    _check(
        failures,
        "diff keeps CRLF out of the marker",
        render_diff("x.md", "colour\r\n", "color\r\n")[-1],
        "+color\r",
    )

    return failures, count


def run_table_selftest(failures: list) -> int:
    """Assert every table entry, not a sample of them.

    A sampled corpus lets a whole entry be deleted without a failing test. Each
    loop below fails per entry, so the tables are covered by construction, and
    the exceptions -- the entries a rule can never reach -- are declared rather
    than assumed.
    """
    count = 0

    # No rule may ever propose a guarded word. NEVER_CONVERT is defence in
    # depth: every entry is currently unreachable, and this assertion is what
    # keeps it that way when a new rule is added.
    count += 1
    _check(
        failures,
        "no rule proposes a guarded word",
        sorted(w for w in NEVER_CONVERT if _apply_once(w) is not None),
        [],
    )

    for table, rule in EXACT_TABLES:
        for british, american in table.items():
            count += 1
            _check(failures, "%s table %s" % (rule, british), convert_text(british), american)

    for stem, american in OUR_STEMS.items():
        count += 1
        _check(failures, "our stem " + stem, convert_text(stem), american)
        count += 1
        _check(failures, "our stem plural " + stem, convert_text(stem + "s"), american + "s")

    for stem, (american, _rule) in RE_STEMS.items():
        count += 1
        _check(failures, "re stem " + stem, convert_text(stem), american)
        count += 1
        _check(failures, "re stem plural " + stem, convert_text(stem + "s"), american + "s")

    for stem in sorted(DOUBLE_L_STEMS):
        count += 1
        _check(failures, "double-l stem " + stem, convert_text(stem + "led"), stem + "ed")
        count += 1
        _check(failures, "double-l stem " + stem, convert_text(stem + "ling"), stem + "ing")

    # Suffix and prefix tables: one nonsense word each is enough to prove the
    # row is wired in, and a missing row fails exactly one assertion.
    for british, american in ISE_SUFFIXES:
        count += 1
        _check(failures, "ise suffix " + british, convert_text("organ" + british), "organ" + american)
    for prefix in sorted(YSE_PREFIXES):
        count += 1
        _check(failures, "yse prefix " + prefix, convert_text(prefix + "yse", aggressive=True)[-3:], "yze")
    for suffix in RE_PLAIN_SUFFIXES:
        count += 1
        _check(failures, "re suffix " + suffix, convert_text("centre" + suffix), "center" + suffix)
    for suffix in RE_DROP_E_SUFFIXES:
        count += 1
        _check(failures, "re drop-e suffix " + suffix, convert_text("centr" + suffix), "center" + suffix)
    for prefix in OUR_PREFIXES:
        count += 1
        _check(failures, "our prefix " + prefix, convert_text(prefix + "colour"), prefix + "color")
    for prefix in RE_PREFIXES:
        count += 1
        _check(failures, "re prefix " + prefix, convert_text(prefix + "centre"), prefix + "center")
    for british, american in AE_OE_PREFIXES:
        count += 1
        _check(failures, "ae-oe prefix " + british, convert_text(british + "ic"), american + "ic")
    for british, american in AE_OE_SUFFIXES:
        count += 1
        _check(failures, "ae-oe suffix " + british, convert_text("tox" + british), "tox" + american)
    for british, american in DOUBLE_L_SUFFIXES:
        count += 1
        _check(failures, "double-l suffix " + british, convert_text("travel" + british), "travel" + american)
    for british, american in SUBSTRING_RULES:
        count += 1
        _check(failures, "substring " + british, convert_text("x" + british + "x"), "x" + american + "x")

    # The deny lists. Every entry has to hold on its own: `imprecise` and
    # `inadvisable` reached the -ise rule because the prefix never came off.
    for stem in sorted(ISE_NEVER_STEMS):
        count += 1
        _check(failures, "ise deny " + stem, convert_text(stem), stem)
    for prefix in WORD_PREFIXES:
        for stem in ("precise", "advisable", "premise"):
            count += 1
            _check(
                failures,
                "ise deny through prefix %s+%s" % (prefix, stem),
                convert_text(prefix + stem),
                prefix + stem,
            )
    # `-is` nouns: the singular has no -ise verb in it, and neither does the
    # `-ises` plural.
    for stem in sorted(ISE_NOUN_STEMS):
        count += 1
        _check(failures, "is-noun " + stem, convert_text(stem), stem)
        count += 1
        _check(failures, "is-noun plural " + stem, convert_text(stem + "es"), stem + "es")

    for phrase in PROTECTED_PHRASES:
        text = " ".join(phrase)
        count += 1
        _check(failures, "protected phrase " + text, convert_text(text), text)
    for (previous, word), american in CONTEXT_BY_PREVIOUS.items():
        count += 1
        _check(
            failures,
            "context before %s %s" % (previous, word),
            convert_text(previous + " " + word),
            previous + " " + american,
        )
    for (word, following), american in CONTEXT_BY_NEXT.items():
        count += 1
        _check(
            failures,
            "context after %s %s" % (word, following),
            convert_text(word + " " + following),
            american + " " + following,
        )
    for phrase, (american, _rule) in PHRASE_RULES.items():
        count += 1
        _check(failures, "phrase rule " + " ".join(phrase), convert_text(" ".join(phrase)), american)

    for key in sorted(PROSE_FRONTMATTER_KEYS):
        document = "---\n%s: a colour guide\n---\n" % key
        count += 1
        _check(
            failures,
            "frontmatter prose key " + key,
            convert_text(document),
            document.replace("colour", "color"),
        )
    for key in ("name", "tools", "argument-hint", "model"):
        document = "---\n%s: colour\n---\n" % key
        count += 1
        _check(failures, "frontmatter data key " + key, convert_text(document), document)

    for word in sorted(PROPER_WHEN_CAPITALISED):
        for form in (word[:1].upper() + word[1:], word.upper()):
            count += 1
            _check(failures, "capitalised name " + form, convert_text(form), form)

    for word in sorted(AMBIGUOUS):
        findings, _ = scan_text(word, "<t>")
        count += 1
        _check(failures, "ambiguous flagged " + word, [f.ambiguous for f in findings], [True])
        count += 1
        _check(failures, "ambiguous not written " + word, convert_text(word), word)
        count += 1
        _check(
            failures,
            "ambiguous written under --aggressive " + word,
            convert_text(word, aggressive=True) != word,
            True,
        )
    return count


def run_cli_selftest(failures: list) -> int:
    """The command line as an agent drives it: streams, exit codes, payloads."""
    count = 0

    # --stdin is a filter: stdout is the document and nothing else.
    count += 1
    _check(failures, "stdin filters", _stdin_main(b"The colour\n", ["--stdin"]), (EXIT_OK, b"The color\n"))
    count += 1
    _check(
        failures,
        "stdin keeps stdout pure with --stats",
        _stdin_main(b"colour\n", ["--stdin", "--stats"])[1],
        b"color\n",
    )
    # Bad bytes are an IO error, not a findings result and not a traceback.
    count += 1
    _check(failures, "stdin rejects non-UTF-8", _stdin_main(b"\xff\xfe bad\n", ["--stdin"]), (EXIT_ERROR, b""))
    count += 1
    _check(failures, "stdin rejects --json", _stdin_main(b"colour\n", ["--stdin", "--json"])[0], EXIT_ERROR)

    # --no-rule takes the labels the findings print, both tiers included.
    count += 1
    _check(failures, "no-rule ambiguous", scan_text("a disc here", "<t>", frozenset({"ambiguous"}))[0], [])
    count += 1
    _check(failures, "no-rule proper-noun", scan_text("Earl Grey tea", "<t>", frozenset({"proper-noun"}))[0], [])
    count += 1
    _check(
        failures,
        "no-rule ambiguous keeps the certain tier",
        convert_text("colour", disabled=frozenset({"ambiguous"})),
        "color",
    )
    count += 1
    _check(
        failures,
        "no-rule accepts a tier name",
        _silent_main(["--check", "--quiet", "--no-rule", "proper-noun", __file__]) in (0, 1),
        True,
    )

    # --version is an assertable pin for a skill.
    try:
        _silent_main(["--version"])
        version_exit = None
    except SystemExit as exc:
        version_exit = exc.code
    count += 1
    _check(failures, "version exits 0", version_exit, 0)

    # --check --aggressive must not describe the opposite of what it will do.
    flagged, _ = scan_text("a disc here", "<t>")
    count += 1
    _check(
        failures,
        "aggressive report header",
        "applied under --aggressive" in "\n".join(render_text_report([("x", flagged)], True)),
        True,
    )
    count += 1
    _check(
        failures,
        "plain report header",
        "not applied without --aggressive" in "\n".join(render_text_report([("x", flagged)], False)),
        True,
    )

    # --no-ambiguous must not leave the stats counting what it filtered out.
    mixed, totals = scan_text("The colour and a disc.\n", "<t>")
    kept = [("x", [f for f in mixed if not f.ambiguous])]
    trimmed = restrict_stats(totals, kept)
    count += 1
    _check(failures, "restricted stats count the kept findings", trimmed.findings, 1)
    count += 1
    _check(failures, "restricted stats drop the filtered tier", trimmed.ambiguous, 0)
    count += 1
    _check(failures, "restricted stats keep the file counters", trimmed.files, totals.files)

    payload = json.loads(render_write_json([("x.md", mixed, 1, True)], totals))
    count += 1
    _check(failures, "write json counts", (payload["files"][0]["applied"], payload["files"][0]["flagged"]), (1, 1))
    payload = json.loads(render_diff_json([("x.md", ["--- a/x.md"])], totals))
    count += 1
    _check(failures, "diff json carries the patch", payload["files"][0]["diff"], "--- a/x.md")

    # A directive nobody recognises has to say so.
    count += 1
    _check(failures, "unknown directive warns", len(directive_warnings("<!-- engb:bogus -->\n", "x.md")), 1)
    count += 1
    _check(failures, "known directive is quiet", directive_warnings("<!-- engb:ignoreline -->\n", "x.md"), [])
    count += 1
    _check(failures, "unrelated comment is quiet", directive_warnings("<!-- TODO: colour -->\n", "x.md"), [])

    # One bad path must neither discard findings nor half-apply a tree.
    with tempfile.TemporaryDirectory() as folder:
        first = Path(folder) / "first.md"
        first.write_text("The colour and a disc.\n", encoding="utf-8")
        last = Path(folder) / "last.md"
        last.write_text("The behaviour here.\n", encoding="utf-8")
        missing = str(Path(folder) / "missing.md")

        code, out = _captured_main(["--check", str(first), missing, str(last)])
        count += 1
        _check(failures, "check exits 2 on a bad path", code, EXIT_ERROR)
        count += 1
        _check(failures, "check keeps the findings it computed", "colour -> color" in out, True)

        # A consumer that summarises from `stats` must not report findings the
        # payload cannot list.
        payload = json.loads(_captured_main(["--check", "--no-ambiguous", "--json", str(first)])[1])
        listed = sum(len(entry["findings"]) for entry in payload["files"])
        count += 1
        _check(
            failures,
            "json stats agree with the payload",
            (payload["stats"]["findings"], listed),
            (1, 1),
        )
        count += 1
        _check(failures, "json stats keep the file counters", payload["stats"]["files"], 1)

        code = _silent_main(["--write", str(first), missing, str(last)])
        count += 1
        _check(failures, "write exits 2 on a bad path", code, EXIT_ERROR)
        count += 1
        _check(
            failures,
            "write applies before the bad path",
            first.read_text(encoding="utf-8"),
            "The color and a disc.\n",
        )
        count += 1
        _check(
            failures,
            "write continues after the bad path",
            last.read_text(encoding="utf-8"),
            "The behavior here.\n",
        )

        code, out = _captured_main(["--write", str(first)])
        count += 1
        _check(
            failures,
            "write is idempotent",
            (code, first.read_text(encoding="utf-8")),
            (EXIT_OK, "The color and a disc.\n"),
        )
        count += 1
        _check(failures, "write names what it left behind", "flagged, left for review" in out, True)
        count += 1
        _check(failures, "write --quiet prints nothing", _captured_main(["--write", "--quiet", str(first)])[1], "")
        count += 1
        _check(
            failures,
            "check --quiet --json prints nothing",
            _captured_main(["--check", "--quiet", "--json", str(first)])[1],
            "",
        )
        code, out = _captured_main(["--diff", str(first)])
        count += 1
        _check(failures, "diff of a converted file is empty", (code, out), (EXIT_OK, ""))
    return count


def run_selftest_cli() -> int:
    failures, count = run_selftest()
    count += run_table_selftest(failures)
    count += run_cli_selftest(failures)
    if failures:
        print("FAIL: %d of %d assertion(s)" % (len(failures), count))
        for failure in failures:
            print("  - " + failure)
        return EXIT_FINDINGS
    print("PASS: %d assertion(s)" % count)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
