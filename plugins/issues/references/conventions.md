# issues plugin — shared conventions

Building blocks the `/issue-*` skills point back to so each skill stays focused on its own logic. Bash snippets target macOS (BSD) and Linux (GNU). When commands differ, switch on `uname`.

## Locate the issues directory

`docs/issues/` is resolved relative to the repo root:

```bash
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
[ -z "$ROOT" ] && { echo "Not inside a git repo."; exit 1; }
ISSUES_DIR="$ROOT/docs/issues"
```

If the user isn't in a git repo, ask whether they want to run `git init` first — issue history without version control is fragile, and the branch-on-start workflow assumes git is present.

## Detect existing setup

```bash
ls "$ISSUES_DIR"/[0-9][0-9][0-9][0-9]-*.md 2>/dev/null | head -1
```

- Output → tickets already exist; the system is set up. Don't re-init.
- No output but the directory exists → seed `README.md` / `INDEX.md` are likely there or coming.
- Directory missing → scaffold (see `issue-init`).

## Find the next ID

Scan existing tickets, take the highest 4-digit prefix, add one:

```bash
last=$(ls "$ISSUES_DIR"/[0-9][0-9][0-9][0-9]-*.md 2>/dev/null \
  | sed 's|.*/||; s|-.*||' \
  | sort -n | tail -1)
next_id=$(printf "%04d" $((10#${last:-0} + 1)))
```

The `10#` prefix forces base-10. Without it, bash interprets `0042` as octal — `042` becomes `34` and `008` errors out with "value too great for base." Apply this trick to any zero-padded counter.

Empty directory → `last` is empty → `${last:-0}` becomes `0` → `next_id` becomes `0001`. The 4-digit pad keeps directories sortable up to 9999; the formula naturally produces `10000` after that, no code change needed.

**Collision defense.** Two sessions racing might compute the same `next_id`. Right before writing, check the slot is still empty:

```bash
attempt=0
while compgen -G "$ISSUES_DIR/${next_id}-*.md" > /dev/null; do
  attempt=$((attempt + 1))
  [ "$attempt" -ge 5 ] && { echo "Too many ID collisions, aborting."; exit 1; }
  next_id=$(printf "%04d" $((10#$next_id + 1)))
done
```

## Slugify a title

Lowercase, replace non-alphanumeric with `-`, collapse runs, trim, cap at 50 chars at a word boundary:

```bash
slug=$(printf '%s' "$title" \
  | tr '[:upper:]' '[:lower:]' \
  | sed 's|[^a-z0-9]|-|g; s|--*|-|g; s|^-||; s|-$||' \
  | cut -c1-50 \
  | sed 's|-$||')
[ -z "$slug" ] && slug="issue-${next_id}"
```

The fallback handles all-punctuation titles. Without it the filename becomes `0042-.md` and breaks the glob conventions used elsewhere.

## Resolve a target (id-or-slug)

`/issue-start` and `/issue-close` accept either `16` (numeric) or `invoicing-missing` (slug fragment).

```bash
resolve_target() {
  local q="$1"
  local matches=()
  if [[ "$q" =~ ^[0-9]+$ ]]; then
    local padded
    padded=$(printf "%04d" "$((10#$q))")
    shopt -s nullglob
    matches=( "$ISSUES_DIR/${padded}-"*.md )
    shopt -u nullglob
  else
    while IFS= read -r line; do
      [ -n "$line" ] && matches+=("$line")
    done < <(grep -li "$q" "$ISSUES_DIR"/[0-9]*.md 2>/dev/null)
  fi
  case "${#matches[@]}" in
    0) echo "no-match"; return 1 ;;
    1) echo "${matches[0]}"; return 0 ;;
    *) printf '%s\n' "${matches[@]}"; return 2 ;;
  esac
}
```

`shopt -s nullglob` stops bash from returning the literal pattern when nothing matches. The read-loop avoids `mapfile` (not available in macOS's default bash 3.2).

When ambiguous (`return 2`), list candidates and ask the user which one. When no match (`return 1`), report and stop.

## Compute "today"

```bash
today=$(date "+%Y-%m-%d")
```

Use this everywhere instead of inlining the format string — single source of truth makes the skill testable.

## Branch naming convention

`{domain}/{kebab-case-description}`. Domains are a hint, not a strict list — projects can extend them. Common starters:

| Domain | Use for |
|---|---|
| `fix/...` | Bugfixes that aren't security |
| `feature/...` | New functionality |
| `frontend/...` | UI-only changes |
| `security/...` | Auth, RBAC, CSP, secrets handling |
| `db/...` | Schema, migrations, indexes |
| `ci/...` | Build/test/release infrastructure |
| `docs/...` | Documentation-only changes |
| `chore/...` | Dependency bumps, lint, formatting |

Pull the planned branch name from the ticket file if it lists one. Otherwise propose one based on the area and severity, and confirm with the user before creating.

## Ticket file template

Used by `issue-init` (in the README) and `issue-new` (filling values from context):

```markdown
# <title>

- **Status:** open
- **Reported:** YYYY-MM-DD
- **Type:** bug | feature | question | discovery
- **Severity:** low | medium | high | critical
- **Area:** <free-form, e.g. frontend, server, db, infra>
- **Source:** <where this came from — meeting, PR review, support ticket, etc.>
- **Fixed:** <set on close — YYYY-MM-DD (commit <short-sha>)>

## Symptom
What the user sees / what's broken.

## Reproduction
Steps to reproduce, including any specific data, role, or environment.

## Root cause
Why it happens — not what the fix is.

## Fix
What changed, and which files.

## Verification
How you confirmed it's fixed (test name, manual steps, screenshot reference).
```

Status transitions: `open → in-progress → fixed`. Alternative terminal states: `blocked` (waiting on someone/something), `wontfix` (closed without changes).

## INDEX.md structure

Hand-maintained board. Edit when a status flips — move the line between sections; don't try to auto-generate.

```markdown
# Issues — Board

At-a-glance status across all tickets in this folder. Hand-maintained: when you flip a ticket's `**Status:**`, move its line to the matching section here. Convention and template live in [`README.md`](./README.md).

Each line: `[NNNN](./NNNN-slug.md) — title — \`branch/name\` — notes`.

## In progress
_(none)_

## Open
_(none yet — use /issue-new to create one)_

## Awaiting input
_(blocked on external decision or info)_

## Done
_(closed tickets with commit SHA)_
```

Projects can split "Open" into priority tiers (`Open — P0`, `Open — high`, etc.) once they have enough tickets that the flat list gets noisy. Don't impose tiers up front.

## Append a status note to a ticket body

When the user adds context without rewriting structured sections, append a dated note at the end of the file:

```markdown

## YYYY-MM-DD update

<note text>
```

A blank line separates the note from prior content. If the file lacks a trailing newline, add one first.

## Updating the `**Status:**` line

Match the exact line `- **Status:** <current>` and replace `<current>` with the new value. Don't touch the `**Reported:**` date — that's the historical record of first observation.

## Pairing and cross-links

Some tickets ship together because they share a fix surface (same form, same controller, same destination route). Mark them in the INDEX with `— paired with NNNN` and link inside each ticket's body with `[[NNNN-slug]]`. Closed-as-paired tickets each keep their own status flip and Verification section — the work was shared, but the tickets test different things.
