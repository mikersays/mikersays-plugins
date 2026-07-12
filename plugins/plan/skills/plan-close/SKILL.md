---
name: plan-close
description: Close (mark done) a planning item in docs/plan/. Use whenever the user finishes work on a tracked bug/feature/chore/todo — phrases like "I fixed it", "that's done", "ship that off", "close item 7", "mark X complete", "wrap up the search ticket" all trigger this. Sets status to done and stamps the closed date. The file is not deleted or moved — closed items stay in docs/plan/ as the history record.
argument-hint: "[id-or-slug] [reason:\"text\"]"
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# plan-close — mark an item done

Flip an item's `status` to `done`, stamp the `closed:` date, and append a closing note.

## Required reading

- `${CLAUDE_PLUGIN_ROOT}/references/operations.md` § *Locate the plan directory*, § *Resolve a target*, § *Parse the frontmatter*, § *Compute "today"*, § *Append a dated note*, § *Bumping `updated:`*, § *Regenerate docs/plan/README.md*.

If `${CLAUDE_PLUGIN_ROOT}` is unset, resolve relative to this SKILL.md's directory: `../../references/operations.md`.

## 1. Parse `$ARGUMENTS`

First token is the target (numeric ID or slug fragment). Optional `reason:"..."` (quoted) attaches a closing note explaining how/why it was closed — useful for "wontfix" or "obsoleted by X" closures.

If `$ARGUMENTS` is empty, ask which item.

## 2. Resolve the target

Follow operations.md § *Resolve a target*. Ambiguous → list candidates and ask. No match → report and stop.

## 3. Already done?

If the resolved item has `status: done`, print its existing `closed:` date and stop — don't double-close or overwrite the original close date.

## 4. Apply the close

Edit the frontmatter:

- `status:` → `done`
- `closed:` → today (ISO)
- `updated:` → today

Append a dated note to the body. If `reason:` was provided:

```markdown

## <today>

Closed: <reason>
```

Otherwise:

```markdown

## <today>

Closed.
```

## 5. Regenerate the index

Follow operations.md § *Regenerate docs/plan/README.md*.

## 6. Report

Tell the user:

- `Closed <NNN> — <title>` (with the reason, if any)
- Remaining counts: `A open · B in-progress · C blocked`

Do not delete or move the file — closed items remain in `docs/plan/` so the history stays intact. If the user wants to archive old closed items, that's a manual move into `docs/plan/archive/` — the `/plan-*` commands glob `docs/plan/[0-9]*.md` directly so anything in `archive/` is automatically ignored.

Do not commit.
