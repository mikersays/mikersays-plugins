---
name: issue-close
description: Mark a docs/issues/ ticket as fixed after the change has shipped. Trigger when the user says "close ticket NNNN", "mark NNNN fixed", "ship issue 0010", "the invoicing bug is done", or after a successful merge of an issue branch. Stamps the merge commit SHA, requires a filled Verification section, and moves the INDEX.md line to Done. Diagnosis-preserving cousin of /plan-close.
argument-hint: "[id-or-slug] [verified:\"what you actually tested\"]"
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# issue-close — mark a ticket fixed

Flip a ticket's `**Status:**` to `fixed`, stamp the merge commit SHA, capture what was verified, and move the INDEX line to Done. Closed tickets stay in `docs/issues/` as the history record — never delete or move them.

## Required reading

- `../../references/conventions.md` (at the plugin root, relative to this skill directory) — read these sections when you reach the matching step: *Locate the issues directory*, *Resolve a target*, *Compute "today"*, *Updating the `**Status:**` line*, *INDEX.md structure*, *Pairing and cross-links*.

## 1. Parse `$ARGUMENTS`

First token is the target (numeric ID or slug fragment). Optional `verified:"..."` (quoted) provides the verification text directly without a follow-up question.

If `$ARGUMENTS` is empty, ask which ticket.

## 2. Resolve the target

Follow conventions.md § *Resolve a target*. Ambiguous → list candidates and ask. No match → report and stop.

## 3. Already fixed?

If the resolved ticket has `**Status:** fixed`, print the existing `**Fixed:**` line and stop — don't double-close or overwrite the original close record. If the user genuinely wants to amend the verification on an already-closed ticket, that's an edit, not a re-close; suggest they edit the file directly.

## 4. Insist on verification before closing

Read the ticket's `## Verification` section. If it's empty (or `TBD`, or `Verification` is missing entirely):

- Ask the user what they actually tested. Be specific: which steps, which roles or environments, expected vs. observed.
- If the user can't name what they verified, **stop and don't close**. Closing without verification defeats the value of the ticket file — the next person hitting the same bug should trust that "fixed" means it was actually tested.

If `verified:"..."` was passed as an argument, use that text directly and skip the question.

## 5. Get the commit SHA

Pick by condition, not by whichever command prints something first:

```bash
# Use HEAD ONLY if you're on the ticket's issue branch or the HEAD
# commit message references the ticket — otherwise HEAD is unrelated.
git log -1 --format=%h

# Otherwise (merged via gh / GitHub UI) → look up the merge commit on main
default_branch=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|.*/||')
: "${default_branch:=main}"   # origin/HEAD may be unset on non-cloned remotes
git log "$default_branch" --grep="<NNNN>" --oneline -1
```

If neither condition yields a clear answer, ask the user for the commit SHA directly (they'll usually have it from `gh pr merge` output or the PR page). Never stamp a SHA you can't tie to the ticket — it goes into the permanent `**Fixed:**` record.

## 6. Apply the close

Edit the ticket file:

- `- **Status:** <current>` → `- **Status:** fixed` — match whatever the current value is (usually `in-progress`, but `open` or `blocked` tickets can be closed directly); see conventions.md § *Updating the `**Status:**` line*
- Fill the `**Fixed:**` line with `YYYY-MM-DD (commit <short-sha>)`
- Fill (or extend) the `## Verification` section with what the user reported in step 4. Use a short bullet list when multiple things were tested:

  ```markdown
  ## Verification

  - Reproduced the original symptom on main: <observed>
  - After fix: <observed>
  - Tested as <role/env>: <result>
  ```

Don't rewrite the `## Symptom`, `## Reproduction`, or `## Root cause` sections — those are the historical diagnosis record. They stay as-is unless they were obviously wrong, in which case append a dated correction note rather than overwriting.

## 7. Paired tickets

If the work shipped as a paired PR (mentioned in the ticket with `[[NNNN-slug]]` cross-links or in the INDEX as `— paired with NNNN`):

- Close both ticket files in the same turn.
- Both get the same commit SHA and the same `**Fixed:**` date.
- Each keeps its own `## Verification` — the two tickets typically test different observable behaviors even when shipped together. Ask separately for each ticket's verification text if it isn't already obvious.

## 8. Update INDEX.md

In `docs/issues/INDEX.md`:

- Remove the line from "In progress" (or wherever it was).
- Append under **Done** with the commit SHA and date:

  ```markdown
  - [<NNNN>](./<NNNN>-<slug>.md) — <title> — fixed <YYYY-MM-DD> (`<short-sha>`)
  ```

If paired, append both lines.

## 9. Report

Tell the user:

- `Closed <NNNN> — <title>` (and the paired ticket if any) — with the commit SHA
- Updated `## Verification` summary (one line)
- Remaining open counts (parse `**Status:**` lines across the directory or count INDEX entries by section)
- A reminder that this skill did **not** commit anything — the user reviews the diff and ships when ready (often via `/ship`)

## What not to do

- Don't delete or rename the ticket file. The whole point of per-issue files is that they persist as searchable history.
- Don't fabricate verification text. If the user hasn't tested, say so and don't close.
- Don't run `git push` or open a PR. Closing is a documentation step, not a ship step.
