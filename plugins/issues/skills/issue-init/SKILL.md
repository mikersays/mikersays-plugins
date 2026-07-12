---
name: issue-init
description: Bootstrap a docs/issues/ folder in the current repo for tracking bugs, features, and incidents as one markdown file per issue. Use whenever the user wants to set up issue tracking inside a repo, asks for a "ticket folder" / "bug tracker folder" / "docs/issues directory", or before they file the first ticket. /issue-new auto-inits if missing, so /issue-init is primarily for explicit setup or for refreshing the seed README/INDEX. This is the bug-write-up cousin of /plan-init — pick this one when issues need a full diagnosis record (symptom, repro, root cause, fix, verification) and a branch-on-start workflow.
allowed-tools: Bash, Read, Write
---

# issue-init — bootstrap docs/issues/

Create the `docs/issues/` directory and seed `README.md` + `INDEX.md`. After this runs, the user can file tickets with `/issue-new`.

## 1. Locate target

Find the repo root:

```bash
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
```

If the user isn't in a git repo, stop and ask whether they want to `git init` first — issue history without version control is fragile, and the branch-on-start workflow assumes git is present. Don't proceed silently.

Target directory: `$ROOT/docs/issues/`.

## 2. Check for an existing setup

If `docs/issues/` already exists, scan for ticket files:

```bash
ls "$ROOT/docs/issues"/[0-9][0-9][0-9][0-9]-*.md 2>/dev/null | head -1
```

- Output → the system is already set up. Report current open/in-progress/fixed counts (plus blocked/wontfix if present — parse the `**Status:**` line in each file) and stop. The user probably wanted `/issue-new` or to look at `INDEX.md`.
- No output but the directory exists → continue; just refresh the README and INDEX skeletons. If `README.md` or `INDEX.md` already exists with content that differs from the seeds below, show the user what would be replaced and confirm before overwriting — don't silently destroy customizations.

## 3. Create the directory

```bash
mkdir -p "$ROOT/docs/issues"
```

## 4. Write the seed README

Write `$ROOT/docs/issues/README.md` with this content verbatim:

````markdown
# Issues

One markdown file per issue. Use this folder for anything that benefits from its own page: a reproducible bug, a regression investigation, a one-off incident, or a fix with non-obvious context.

The board lives in [`INDEX.md`](./INDEX.md) — open that to see what's in-flight, what's queued, and what's done.

## File naming

`NNNN-short-kebab-slug.md` — zero-padded 4-digit sequence, then a slug.

Examples:
- `0001-uploads-static-route-leaks-evidence.md`
- `0002-activity-log-missing-ip-address.md`

## Template

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

## Commands

- `/issue-new <title>` — file a new ticket. Auto-numbers, asks for type / area / severity.
- `/issue-start <id-or-slug>` — begin work. Aligns the plan with you first, then creates a `{domain}/{kebab}` branch and flips status to in-progress.
- `/issue-close <id-or-slug>` — mark fixed after the change has shipped. Fills commit SHA, prompts for Verification, moves the INDEX line to Done.

Edit individual tickets and `INDEX.md` directly when needed — the commands are conveniences, not gatekeepers.
````

## 5. Write the seed INDEX

Write `$ROOT/docs/issues/INDEX.md` with this content verbatim:

````markdown
# Issues — Board

At-a-glance status across all tickets in this folder. Hand-maintained: when you flip a ticket's `**Status:**`, move its line to the matching section here. Convention and template live in [`README.md`](./README.md).

Each line: ``[NNNN](./NNNN-slug.md) — title — `branch/name` — notes``.

## In progress

_(none)_

## Open

_(none yet — use `/issue-new` to create one)_

## Awaiting input

_(blocked on external decision or info)_

## Done

_(closed tickets with commit SHA)_
````

A flat "Open" section is the default. Once a project accumulates enough tickets that triage by priority would help, split `Open` into tiers (`Open — P0`, `Open — high`, `Open — medium`). Don't impose tiers up front.

## 6. Report

Tell the user:
- Directory created at `docs/issues/`.
- `README.md` and `INDEX.md` are seeded.
- Next step: `/issue-new <title>` to file the first ticket.
- Suggest staging the new directory with `git add docs/issues/` (don't run it yourself — let them review).

Do not commit.
