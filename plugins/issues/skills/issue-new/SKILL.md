---
name: issue-new
description: File a new ticket under docs/issues/ for a bug, feature request, incident, or open question that should be tracked but isn't being fixed right now. Trigger whenever the user says "log this as a bug", "open a ticket for X", "track this issue", "create an issue for Y", "we should remember to fix Z", or describes something worth filing — even when they don't explicitly say "ticket". Auto-initializes the docs/issues/ scaffolding if missing, picks the next NNNN, writes the file with the template pre-filled from conversation context, and updates docs/issues/INDEX.md so the board stays current. Reach for this skill instead of /plan-add when the issue needs a real diagnosis record (symptom, repro, root cause, fix, verification) rather than a quick todo line.
argument-hint: "[title — describe the bug or request]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# issue-new — file a new ticket

Create a new ticket file in `docs/issues/` and add it to the board. One ticket per real issue; don't lump multiple symptoms into one file.

## Required reading

- `references/conventions.md` — read these sections when you reach the matching step: *Locate the issues directory*, *Find the next ID*, *Slugify a title*, *Ticket file template*, *INDEX.md structure*.

## 1. Parse `$ARGUMENTS`

`$ARGUMENTS` is the user's free-text description of the issue (often the title itself plus context). If empty, ask the user for at least a one-line title before proceeding.

Inline modifiers the user might include (parse and pull them out of the title):

| Token | Effect |
|---|---|
| `type:<bug\|feature\|question\|discovery>` | sets the **Type** line |
| `severity:<low\|medium\|high\|critical>` | sets the **Severity** line |
| `area:<free-form>` | sets the **Area** line (frontend, server, db, …) |
| `source:"<text>"` | sets the **Source** line (where it came from) |

Everything else stays in the title.

## 2. Apply defaults and infer where reasonable

If the user didn't specify them explicitly:

- **Type** — infer from the title's verbs as a soft default: `fix|broken|crash|error|bug|leak|race` → `bug`; `add|build|implement|new|support|allow` → `feature`; `?` or `how do we` or `should we` → `question`; otherwise leave blank and ask.
- **Severity** — leave blank and ask (`low | medium | high | critical`). Don't guess severity; it's the user's call.
- **Area** — best guess from the title (e.g., "Save button" → `frontend`, "migration" → `db`). Confirm with the user.
- **Source** — pull from the conversation if obvious ("user reported", "found in PR review", "from the May 19 notes"). Otherwise leave blank.

Mention inferred values in the final report so the user can correct them by editing the file.

## 3. Locate the directory, auto-init if missing

Resolve `$ISSUES_DIR` (conventions.md § Locate the issues directory). If the directory doesn't exist:

- Create it with `mkdir -p`.
- Write the seed `README.md` and `INDEX.md` (same content as `/issue-init` step 4 and step 5).
- Mention "(initialized docs/issues/)" in your report.

Don't make the user run `/issue-init` first. One command is friendlier.

## 4. Compute ID and slug

Follow conventions.md § *Find the next ID* and § *Slugify a title*.

## 5. Write the ticket

Filename: `$ISSUES_DIR/<NNNN>-<slug>.md`. Verify the slot is still empty (collision check from conventions.md § Find the next ID); if not, bump and retry up to 5 times.

Fill the template from conventions.md § *Ticket file template*. For each section:

- **Symptom** — write what the user described, in their words where possible. If they pasted an error or log line, include it verbatim.
- **Reproduction** — if the user gave repro steps, list them. If not, leave a one-line placeholder like `TBD — needs reproduction steps.` and ask the user later. Don't invent steps.
- **Root cause** — usually `Unknown — needs investigation.` at file time. Don't speculate without evidence; the diagnosis happens during `/issue-start`.
- **Fix** — leave as `TBD`. The fix isn't decided until alignment.
- **Verification** — leave empty. `/issue-close` fills this with what was actually tested.

Pre-fill `**Reported:** <today>` (conventions.md § Compute "today"). Leave `**Fixed:**` blank — `/issue-close` sets it.

## 6. Update INDEX.md

Append a line to the **Open** section of `$ISSUES_DIR/INDEX.md`:

```markdown
- [<NNNN>](./<NNNN>-<slug>.md) — <title>
```

If the ticket clearly belongs to "Awaiting input" instead (it's a question or needs an external decision), put it there with a short note: `— blocked on <who/what>`.

Don't try to auto-sort by severity. Append at the end of the relevant section; the user can reorder by hand if they care.

## 7. Search for duplicates first

Before completing, grep `$ISSUES_DIR` for keywords from the title:

```bash
grep -li "<keyword>" "$ISSUES_DIR"/[0-9]*.md 2>/dev/null
```

If anything matches, mention it to the user and ask whether to file separately or update the existing ticket instead. Duplicates fragment context.

## 8. Report

Tell the user:

- Relative path of the new ticket file
- Resolved NNNN, type, severity, area
- Anything you inferred (so they can override by editing)
- A nudge that the next step is `/issue-start <NNNN>` when they're ready to work it — emphasizing the alignment-before-implementing rule built into that skill.

Do not commit. Do not run `git add` — let the user review and stage themselves.
