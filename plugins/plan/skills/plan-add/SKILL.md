---
name: plan-add
description: Create a new planning item (bug, feature, chore, or todo) as a markdown file inside docs/plan/. Use this whenever the user wants to track a new bug, feature, todo, follow-up, issue, or piece of deferred work in their repo — including phrases like "log this", "track this", "remember to", "I need to fix", "add this to the plan", or any "we should do X later" request. Auto-initializes docs/plan/ if it doesn't exist yet.
argument-hint: "[title — optionally with type:bug priority:high due:friday tag:auth]"
allowed-tools: Bash, Read, Write, Glob
---

# plan-add — create a new item

Create a new markdown file in `docs/plan/` representing a single piece of planned work.

## Required reading

- `${CLAUDE_PLUGIN_ROOT}/references/schema.md` — canonical frontmatter fields and allowed values.
- `${CLAUDE_PLUGIN_ROOT}/references/operations.md` — read these sections when you reach the corresponding step: *Locate the plan directory*, *Find the next ID*, *Slugify a title*, *Normalize a date*, *Regenerate docs/plan/README.md*.

If `${CLAUDE_PLUGIN_ROOT}` is unset, resolve relative to this SKILL.md's directory: `../../references/schema.md` and `../../references/operations.md`.

## 1. Parse `$ARGUMENTS`

`$ARGUMENTS` can mix free-text title with inline modifiers:

| Token | Effect |
|---|---|
| `type:<bug\|feature\|chore\|todo>` | sets `type:` |
| `priority:<high\|med\|low>` | sets `priority:` |
| `due:<date-or-word>` | sets `due:` (normalize via operations.md) |
| `tag:<name>` | adds a tag (repeat for multiple) |
| anything else | concatenated into the title |

If `$ARGUMENTS` is empty, ask the user for at least a title before proceeding.

## 2. Apply defaults

If the user didn't specify them explicitly:

- `type` — infer from title verbs as a soft default: `fix|broken|crash|error|bug` → `bug`; `add|build|implement|new|support` → `feature`; `update|refactor|cleanup|bump|migrate` → `chore`; otherwise `todo`.
- `status` — `open`.
- `priority` — `med`.
- `due` — absent (omit the line).

Mention inferred values in the final report so the user can override with `/plan-update`.

## 3. Locate target, auto-init if missing

Resolve `$PLAN_DIR` (operations.md § Locate the plan directory). If the directory doesn't exist:

- Create it (`mkdir -p`).
- Write the seed `README.md` — copy the content verbatim from step 4 of `${CLAUDE_PLUGIN_ROOT}/skills/plan-init/SKILL.md` (relative to this SKILL.md's directory: `../plan-init/SKILL.md`).
- Mention "(initialized docs/plan/)" in your report.

Don't make the user run `/plan-init` first. One command is friendlier.

## 4. Compute ID and slug

Follow operations.md § *Find the next ID* and § *Slugify a title*.

## 5. Normalize `due` if present

Follow operations.md § *Normalize a date*. If parsing fails, ask the user for an ISO date — don't guess.

## 6. Write the item

Filename: `$PLAN_DIR/<NNN>-<slug>.md`. Verify the slot is still free (collision check from operations.md § Find the next ID); if not, bump and retry up to 5 times.

Use this template, omitting empty optional fields:

```markdown
---
id: <NNN>
title: <title>
type: <type>
status: open
priority: <priority>
due: <due>
tags: [<tags>]
created: <today>
updated: <today>
closed:
---

<one-line description, or blank line if the title is self-explanatory>
```

Rules for the frontmatter:

- Drop the `due:` line entirely when there's no deadline. Don't write `due:` with empty value.
- Drop the `tags:` line when there are no tags. Don't write `tags: []`.
- Leave `closed:` empty — it exists as a placeholder; `/plan-close` will fill it.

## 7. Regenerate the index

Follow operations.md § *Regenerate docs/plan/README.md*.

## 8. Report

Tell the user:

- Relative path to the new item file
- Resolved ID, type, priority, due (if any)
- Any defaults you inferred (so they can override)
- The relative path of the regenerated `docs/plan/README.md`

Do not commit. Do not run `/ship` or any git command beyond `git rev-parse`.
