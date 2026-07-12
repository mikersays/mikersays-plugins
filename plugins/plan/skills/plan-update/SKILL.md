---
name: plan-update
description: Update an existing planning item in docs/plan/ — change its status, priority, due date, type, tags, or append a dated note. Use whenever the user wants to mark something in-progress, change a deadline, raise/lower priority, unblock something, retitle, or add a comment/note to a tracked item. Accepts either the numeric ID or a slug fragment from the title. Phrases like "start work on 7", "push X to next week", "mark item Y blocked", "add a note to the search ticket" all trigger this.
argument-hint: "[id-or-slug] [status:in-progress] [priority:high] [due:friday] [tag:auth] [note:\"text\"]"
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# plan-update — edit an existing item

Modify one or more frontmatter fields, and/or append a dated note to the body.

## Required reading

- `${CLAUDE_PLUGIN_ROOT}/references/schema.md` for allowed field values.
- `${CLAUDE_PLUGIN_ROOT}/references/operations.md` § *Locate the plan directory*, § *Resolve a target*, § *Normalize a date*, § *Append a dated note*, § *Bumping `updated:`*, § *Regenerate docs/plan/README.md*.

If `${CLAUDE_PLUGIN_ROOT}` is unset, resolve relative to this SKILL.md's directory: `../../references/schema.md` and `../../references/operations.md`.

## 1. Parse `$ARGUMENTS`

First token is the target (numeric ID or slug fragment). Remaining tokens are modifiers:

| Modifier | Effect |
|---|---|
| `status:<value>` | change status (open / in-progress / blocked / done) |
| `priority:<value>` | high / med / low |
| `type:<value>` | bug / feature / chore / todo |
| `due:<value>` | ISO date or natural language; `due:none` clears it |
| `title:"<new>"` | rename frontmatter title; filename stays put |
| `tag:<name>` | add a tag (repeatable) |
| `untag:<name>` | remove a tag |
| `note:"<text>"` | append a dated note to the body |

Quoted values (for `note:` and `title:`) may span spaces. If `$ARGUMENTS` lacks a target, ask which item.

If only a target is given (no modifiers), print the current state of the item and ask what to change. Don't write anything yet.

## 2. Resolve the target

Follow operations.md § *Resolve a target*.

- Single match → proceed.
- Multiple matches → list `ID | title` for each and ask the user to pick.
- No match → report and stop.

## 3. Validate modifiers

For each modifier, check the value is allowed (per `schema.md`). If a value is bogus (e.g., `status:archived`), stop with the list of allowed values — don't silently coerce.

For `due:`, normalize via operations.md § *Normalize a date*. `due:none` removes the line entirely.

## 4. Apply changes

Use `Edit` for surgical frontmatter changes. For each field that's changing:

- **Changing an existing field** — match the existing line and replace. Use the full line including its current value as the `old_string` so the match is unique:
  ```
  old_string: "status: open"
  new_string: "status: in-progress"
  ```
- **Adding a missing field** — use the preceding field's line as the anchor and append a newline + the new field. Field order is `id → title → type → status → priority → due → tags → created → updated → closed`, so:
  ```
  # Adding due (anchor on priority):
  old_string: "priority: med"
  new_string: "priority: med\ndue: 2026-05-25"

  # Adding tags (anchor on due if present, else priority):
  old_string: "due: 2026-05-25"
  new_string: "due: 2026-05-25\ntags: [auth]"
  ```
  Read the current frontmatter first to pick the right anchor and capture its exact value — the value is variable, so the literal anchor line differs per item.
- **For `tag:` / `untag:`** — read the current `tags:` line, mutate the bracketed list, write the new line back via Edit. If `tags:` is absent, add it per the rule above. If removing the last tag, the line becomes `tags: []` — delete the line entirely instead of leaving the empty list.

Always bump `updated:` to today, even if only a note was appended.

For `note:"..."`, append after existing body content per operations.md § *Append a dated note*.

For `status:done` — also set `closed:` to today and append `## <today>\n\nClosed.` if no `note:` was provided. `/plan-close` is the cleaner entry point for closing (it accepts a `reason:"..."`), but accepting `status:done` here keeps the update interface composable for bulk edits.

For any status change away from `done` on an item that has a `closed:` line — delete the `closed:` line (schema: `closed` is present iff `status: done`) and append `## <today>\n\nReopened.` if no `note:` was provided.

## 5. Regenerate the index

Follow operations.md § *Regenerate docs/plan/README.md*.

## 6. Report

Print a one-line-per-change diff:

```
status: open → in-progress
due: → 2026-05-25
+ note appended
```

Mention the item's ID and title at the top. Confirm that `docs/plan/README.md` was regenerated.

Do not commit.
