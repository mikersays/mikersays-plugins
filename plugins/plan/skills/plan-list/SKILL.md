---
name: plan-list
description: List planning items in docs/plan/, optionally filtered by status, type, priority, due date, or tag. Use whenever the user wants to see open issues/bugs/todos, check the status of planned work, find overdue items, or get an overview of what's in the plan folder. Phrases like "what's open", "what's due", "show me bugs", "list todos", "what's in the plan", "show overdue work" all trigger this. The default view hides done items.
argument-hint: "[filters like status:open type:bug due:overdue tag:auth]"
allowed-tools: Bash, Read, Glob, Grep
---

# plan-list — list and filter items

Show items from `docs/plan/`, filtered by query, grouped by status, sorted by priority and due date. Read-only — does not modify any files.

## Required reading

- `${CLAUDE_PLUGIN_ROOT}/references/schema.md` for field reference.
- `${CLAUDE_PLUGIN_ROOT}/references/operations.md` § *Locate the plan directory*, § *Parse the frontmatter*, § *Compute "today"*.

If `${CLAUDE_PLUGIN_ROOT}` is unset, resolve relative to this SKILL.md's directory: `../../references/schema.md` and `../../references/operations.md`.

## 1. Parse filters from `$ARGUMENTS`

Each token is a `key:value` pair. Values may be comma-separated (treated as OR within a key); multiple keys AND together.

| Filter | Values |
|---|---|
| `status:` | `open`, `in-progress`, `blocked`, `done`, `all` |
| `type:` | `bug`, `feature`, `chore`, `todo` |
| `priority:` | `high`, `med`, `low` |
| `due:` | `overdue` (`< today`), `today` (`== today`), `this-week` (today ≤ due ≤ today+7 — overdue items match `overdue`, not `this-week`), `any` (has a due), `none` (no due) |
| `tag:` | a tag name (substring match against the `tags:` line) |

**Default** when no filters are supplied: `status:open,in-progress,blocked` — i.e. everything except done.

If a token has an unknown key or a value not listed above, do not guess — report the invalid token, echo the table of valid filters, and stop.

## 2. Locate and scan

Resolve `$PLAN_DIR` (operations.md). If it doesn't exist or contains no `[0-9]*.md` files, report:

> No plan items yet. Create one with `/plan-add <title>`.

…and stop.

Otherwise iterate `$PLAN_DIR/[0-9]*.md` and parse each file's frontmatter.

For `due:` filters, compute `today` once at the start, then compare ISO date strings lexically — `YYYY-MM-DD` sorts correctly as text.

```bash
today=$(date "+%Y-%m-%d")

# For due:this-week, compute the upper bound:
if [ "$(uname)" = "Darwin" ]; then
  end=$(date -v+7d "+%Y-%m-%d")
else
  end=$(date -d "+7 days" "+%Y-%m-%d")
fi
```

For each item with a `due` value, apply the filter using string comparison (POSIX `\<` / `\>` in `[ ]` are lexical and work correctly on ISO dates):

```bash
case "$filter_due" in
  overdue)    [ -n "$due" ] && [ "$due" \< "$today" ] && match=1 ;;
  today)     [ "$due" = "$today" ] && match=1 ;;
  this-week)  [ -n "$due" ] && [ ! "$due" \< "$today" ] && [ ! "$due" \> "$end" ] && match=1 ;;
  any)        [ -n "$due" ] && match=1 ;;
  none)       [ -z "$due" ] && match=1 ;;
esac
```

The `[ ! "$due" \< "$today" ]` form is "due >= today" — POSIX `[ ]` has no `\>=`, so negate `<`. The leading `[ -n "$due" ]` guard prevents an empty `$due` from accidentally matching `overdue` (empty string sorts before every date).

## 3. Render

Group filtered items by status in fixed order: `open`, `in-progress`, `blocked`, `done`. Within each group, sort by:

1. Priority — `high` > `med` > `low`
2. Due ascending — items with `due` come before items without
3. ID descending — newest first

One markdown table per non-empty group:

```markdown
## Open (3)

| ID | Title | Type | Pri | Due | Tags |
|----|-------|------|-----|-----|------|
| 042 | Add search to docs site | feature | high | 2026-06-01 | docs |
| 038 | Cache invalidation on deploy | chore | med | | infra |
| 012 | Investigate flaky test | todo | low | | tests |
```

Render notes:

- Empty cells stay blank (no `-`, no `null`).
- For the `done` group when shown, use columns `ID | Title | Closed` instead of priority/due/tags — those don't matter once it's done.
- If filters produce zero results, say so and echo back the active filter set.

## 4. Tail summary

After the tables, print one line:

```
N items shown · A open · B in-progress · C blocked · D done
```

When the default filter was applied (no `$ARGUMENTS`), add:

```
(use status:all to include done items)
```

## 5. Overdue highlight

If any non-done item in the rendered output has `due < today`, prepend a one-line warning above the first table (a completed item with a past due date is not overdue):

> ⚠ X items are overdue.

Don't repeat the items — they're already visible in the table.
