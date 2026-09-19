---
name: okf-validate
description: Check an Open Knowledge Format (OKF v0.2) bundle for conformance and lint problems — missing frontmatter or type, malformed index.md or log.md, bad timestamps and actor ids, footnotes with no matching source, broken links, stale concepts, incomplete Attested Computation contracts — and report trust tiers (unverified / machine-confirmed / human-reviewed) and lifecycle status across the bundle. Trigger on "okf validate", "check the bundle", "is this bundle conformant", "lint the knowledge bundle", "what's stale", or "audit the OKF docs".
argument-hint: "[bundle directory] [--strict]"
allowed-tools: Bash, Read, Edit, Glob, Grep
---

# okf-validate — conformance and lint

Run the bundled validator, then act on what it says with judgment: fix the mechanical, explain the
human. Read `../../references/okf-spec.md` (plugin root, relative to this skill) when you need the
rule behind a finding.

## Run

Locate the bundle (the directory whose `index.md` frontmatter carries `okf_version`, or the one
the user named), then:

```bash
OKF="${CLAUDE_PLUGIN_ROOT}/scripts/okf.py"
[ -f "$OKF" ] || OKF="$(find ~/.claude/plugins ~/.codex/plugins -path '*/okf/scripts/okf.py' -print -quit 2>/dev/null)"
python3 "$OKF" validate "<bundle>"             # findings + summary; exit 1 on errors
python3 "$OKF" validate "<bundle>" --strict    # warnings fail too
python3 "$OKF" validate "<bundle>" --json      # machine-readable
```

If `find` returns nothing the plugin is not installed where expected; report that and stop.

## Reading the output

Findings are `path[:line]: CODE message`. `E` codes break conformance (§11 of the spec); `W`
codes are SHOULD-level guidance and lint. The summary at the end gives concept and type counts,
trust tiers, status counts, stale count, and the declared `okf_version`.

| Code | Meaning | Usually fixed by |
|---|---|---|
| E001–E003 | no frontmatter, unparseable YAML, missing `type` | you, editing the file |
| E004 | frontmatter on an `index.md` (or extra keys on the root one) | you, or `index --write` |
| E005 | `log.md` heading is not `## YYYY-MM-DD` | you |
| E006 | Attested Computation without `runtime` | you, after asking what runs it |
| W101 | no `description` | you, one sentence from the body |
| W102–W104, W116 | bad timestamp / actor id / `generated` or `verified` shape | you, mechanically |
| W105 | unknown `status` | you: draft, stable, or deprecated |
| W106 | stale (`stale_after` passed) | a human re-verifying; you only flag it |
| W107, W119 | `sources` entry without `resource`; `usage_count` without a window | you, from what you actually know |
| W108 | footnote label with no `sources[].id` | add the source entry or fix the label |
| W110, W111, W114 | broken link / path field / index target | fix the path, or leave a deliberate forward link |
| W112, W113 | Attested Computation missing or doubled computation, weak contract | you, per §10 |
| W115, W120 | index out of sync or missing | `index --write` |
| W117 | no or wrong `okf_version` at root | `index --write`, or edit |
| W118 | v0.1 leftovers (`timestamp`, `# Citations`) | migrate to `generated` / `sources` |
| W121 | log not newest-first | reorder |

## Act with judgment

- **Mechanical findings you can fix without inventing facts**: fix them. Timestamp formats, a
  `human:` prefix the user clearly meant, an index rebuild, a footnote label typo.
- **Findings that need knowledge you don't have**: don't guess. A missing `description` for a
  concept you understand from its body is fine to write; a `sources.resource` you would have to
  make up is not. A stale concept is stale until a human says otherwise; never touch `verified`
  or `stale_after` to silence a warning.
- **Broken links** are legal OKF. Only "fix" one when it is a typo; a link to not-yet-written
  knowledge is information, and the right answer may be "these three concepts are missing".
- **Trust summary**: if most of the bundle is unverified, say so plainly and name the concepts a
  human should sign off on first (the ones other concepts link to most, and any Attested
  Computation).

Re-run after fixing. Report the before/after counts, what you changed, and what is left for a
person. Do not commit.
