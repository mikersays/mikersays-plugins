---
name: plan-init
description: Bootstrap a docs/plan/ folder in the current repo for tracking bugs, issues, chores, and todos as markdown files. Use this whenever the user wants to start a lightweight planning system, set up local issue tracking inside a repo, or asks for a "plan folder" / "todo tracker" / "issues directory" — even before they've used any other /plan-* command. /plan-add will auto-init if missing, so this command is primarily for explicit setup.
argument-hint: ""
allowed-tools: Bash, Read, Write
---

# plan-init — bootstrap docs/plan/

Create the `docs/plan/` directory and seed `README.md`. After this runs, the user can create items with `/plan-add`.

## 1. Locate target

Find the repo root:

```bash
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
```

If the user isn't in a git repo, stop and ask whether they want to `git init` first — planning history is worth almost nothing without version control. Don't proceed silently.

Target: `$ROOT/docs/plan/`.

## 2. Check for an existing setup

If `docs/plan/` already exists, scan for item files:

```bash
ls "$ROOT/docs/plan"/[0-9]*.md 2>/dev/null | head -1
```

- If items exist → the plan system is already set up. Report current counts (per status) and stop. The user probably wanted `/plan-list`.
- If the directory exists but is empty (or only has `README.md`) → continue to step 3 and just refresh the README.

## 3. Create the directory

```bash
mkdir -p "$ROOT/docs/plan"
```

## 4. Write the seed README

Write `$ROOT/docs/plan/README.md` with this content verbatim:

````markdown
# Plan

No items yet. Create one with `/plan-add <title>`.

## How this works

This folder holds one markdown file per planning item — bugs, features, chores, or todos. Each item has YAML frontmatter (id, status, priority, due) and a free-form body. The filename is `NNN-slug.md` where `NNN` is a zero-padded sequential ID.

## Commands

- `/plan-add <title>` — create a new item. Inline modifiers: `type:bug`, `priority:high`, `due:friday`, `tag:auth`.
- `/plan-list [filters]` — list items. Filter by `status:`, `type:`, `priority:`, `due:`, `tag:`. Default hides done.
- `/plan-update <id-or-slug> [field:value]` — change status/priority/due, append a note.
- `/plan-close <id-or-slug>` — mark done and stamp the closed date.

This `README.md` is auto-regenerated. Edit individual items directly, not this file.
````

## 5. Report

Tell the user:
- The directory was created at the relative path `docs/plan/`.
- They can now run `/plan-add <title>` to create the first item.
- Suggest staging the new directory with `git add docs/plan/` (don't run it yourself — let them review).

Do not commit anything.
