# issues

Per-issue bug, feature, and incident tracker that lives inside your repo at `docs/issues/`. One markdown file per ticket — symptom, reproduction, root cause, fix, verification — plus a branch-on-start workflow and a hard rule to align with the user before implementing. No external service, no database, no sync. Just files git tracks.

## Commands

| Command | What it does |
|---|---|
| `/issue-init` | Create `docs/issues/`, seed `README.md` and `INDEX.md`. Optional — `/issue-new` auto-inits. |
| `/issue-new <title>` | File a new ticket. Inline modifiers: `type:bug`, `severity:high`, `area:frontend`, `source:"PR review"`. |
| `/issue-start <id-or-slug>` | Begin work. **Aligns the plan with you first**, then creates a `{domain}/{kebab}` branch and flips status to in-progress. |
| `/issue-close <id-or-slug>` | Mark fixed after the change has shipped. Captures verification, stamps the commit SHA, moves the line to Done in `INDEX.md`. |

## Ticket shape

Each ticket is `docs/issues/NNNN-kebab-slug.md`:

```markdown
# <title>

- **Status:** open
- **Reported:** 2026-05-19
- **Type:** bug
- **Severity:** high
- **Area:** server
- **Source:** Cynthia review, 2026-05-19
- **Fixed:** (set on close)

## Symptom
What the user sees / what's broken.

## Reproduction
Steps, role, environment, sample data.

## Root cause
Why it happens — not what the fix is.

## Fix
What changed, and which files.

## Verification
How you confirmed it's fixed.
```

`docs/issues/INDEX.md` is a hand-maintained board showing all tickets by status (In progress / Open / Awaiting input / Done). Each lifecycle command moves the matching line for you.

## The alignment rule

`/issue-start` enforces a hard rule: **don't write code until the user agrees on the approach.** The skill restates the symptom, shares a root-cause hypothesis (or names what needs read-only investigation first), proposes the minimum fix, names the scope — then stops and waits.

This applies to "trivial" tickets too. The cost of one extra confirmation message is small; the cost of a misaligned fix is large, because the user usually understands the stakeholder context better than the ticket file does.

## Why this shape

- **Per-issue file, never deleted** — closed tickets stay as searchable history. `git log <file>` keeps the diagnosis record meaningful; PR links don't rot; `grep` is trivial.
- **4-digit zero-padded IDs** — sortable, typeable, room for thousands of tickets before the pad overflows naturally to 5 digits.
- **Bug-write-up template, not a todo line** — every ticket has space for symptom, repro, root cause, fix, and verification. The shape rewards real diagnosis and pays off the next time the same kind of bug appears.
- **INDEX.md as the dashboard** — hand-maintained, one line per ticket, sectioned by status. Cheaper than auto-generation for the size most projects need, and easy to extend with priority tiers (`Open — P0`, `Open — high`) once the list grows.
- **Branch-on-start built in** — `/issue-start` creates the `{domain}/{kebab}` branch and pairs the ticket lifecycle with git history.

## Installation

```bash
/plugin install issues@mikersays-plugins
```

## Usage example

```
/issue-new Save Template button does nothing type:bug severity:high area:frontend
/issue-new Drag-and-drop for case-note attachments type:feature area:frontend
/issue-start 1
# (agent restates symptom + proposes minimum fix; you reply "go")
# ...do the work, push, merge...
/issue-close 1 verified:"Save Template now persists the template and shows a success toast; tested as admin and admin_staff"
```

## issues vs. plan

This marketplace ships two markdown-based trackers. Pick by the shape of the work:

| | `plan` | `issues` |
|---|---|---|
| Item shape | Title + short body, YAML frontmatter | Symptom / repro / root cause / fix / verification |
| ID | 3-digit (`042`) | 4-digit (`0042`) |
| Index | Auto-regenerated `README.md` | Hand-maintained `INDEX.md` |
| Workflow | Status field flip | Branch-on-start + alignment-before-implement |
| Best for | Lightweight todos, mixed bug/feature/chore lists | Bug-heavy work that benefits from a real diagnosis record |
| Folder | `docs/plan/` | `docs/issues/` |

They coexist happily — one project can use both, e.g., `docs/plan/` for the loose todo list and `docs/issues/` for the gnarly bugs.

## Constraints

- **Never commits or pushes.** The user reviews diffs and ships when ready (often via `/ship`).
- **Never deletes or moves tickets.** Closed tickets stay forever as the history record.
- **Refuses to operate outside a git repo** — issue history without version control is fragile, and the branch-on-start workflow needs git.
- **macOS and Linux supported** (BSD `date` and GNU `date` both handled). Windows untested.

## Pairing with the rest of the marketplace

After diagnosing and fixing an issue, ship the diff with `/ship` and open a PR with `/pr`. If you want to mirror tickets to GitHub Issues, `gh issue create --body-file docs/issues/NNNN-*.md` does the job — that's a one-off command, not built in.

For larger plan-shaped work (general todos, feature backlogs), see the `plan` plugin. For project-internal write-ups that aren't tied to a single ticket (architecture decisions, retros), keep using whatever convention your repo already has — `issues` is intentionally scoped to per-issue diagnosis.
