---
name: issue-start
description: Begin work on an existing ticket in docs/issues/. Trigger when the user says "start ticket NNNN", "pick up issue 0016", "let's tackle the invoicing bug", "work on the Save Template thing", or otherwise indicates they're starting on something already filed. This skill enforces the project's alignment-before-implementing rule — before any code is written, the agent restates the symptom, shares a root-cause hypothesis (or names what needs read-only investigation first), proposes the minimum fix, and waits for the user to agree. Only then does it flip the ticket's Status to in-progress, create a {domain}/{kebab} branch, and move the line in docs/issues/INDEX.md to "In progress". This is the workflow-heavy cousin of /plan-update — pick this one when the work needs alignment and a dedicated branch, not just a status field flip.
argument-hint: "[id-or-slug — e.g. 16 or invoicing-missing]"
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

# issue-start — begin work on a ticket

Use this at the moment you're switching from "we should fix this" to "I'm fixing this now." The skill encodes a working convention so neither the agent nor the user has to remember it — including the alignment-before-implementing rule, which is the most important step.

## Required reading

- `references/conventions.md` — read these sections when you reach the matching step: *Locate the issues directory*, *Resolve a target*, *Compute "today"*, *Branch naming convention*, *Updating the `**Status:**` line*, *INDEX.md structure*.

## 1. Locate the ticket

Parse `$ARGUMENTS` (numeric ID or slug fragment). If empty, ask which ticket. Resolve via conventions.md § *Resolve a target*. Ambiguous → list candidates and ask. No match → report and stop.

## 2. Read it in full

Read the full ticket file before doing anything else. Pay attention to:

- `## Symptom` and `## Reproduction` — what's actually broken
- `## Root cause` — often "Unknown" or "TBD"; that's the diagnostic work ahead
- Any `[[NNNN-slug]]` cross-links to paired tickets (some tickets ship together; check whether the user means to work them as a pair)
- The `**Severity:**` and `**Area:**` lines — they inform the branch name later

## 3. Align with the user before any implementation

This is a hard rule. After reading the ticket, write back to the user:

- A one-line restatement of the **symptom** (proves you read it).
- Your **hypothesis** for root cause. If the root cause is genuinely unknown, say "I need to investigate first" and name the read-only checks you'd run (log lines, DB queries, grep paths, browser inspection). Read-only investigation is fine to proceed with; implementing a fix is not.
- The **minimum fix** you'd propose, in one or two sentences.
- **Scope:** what's in, what's deliberately out of this ticket.

Then *stop and wait*. Do not flip status, create the branch, or write code in the same turn. The user must explicitly agree (often a "go", "ship it", "yes do it", or a refined plan in response).

This applies to "trivial-looking" tickets too — one-line typos, dead buttons, obvious null checks. The cost of one extra confirmation message is small; the cost of a misaligned fix is large, because the user usually understands the broader stakeholder context (who reported it, what they're really trying to do) better than the ticket file does.

If the user replies with a refinement, integrate it and re-confirm before proceeding. Don't move past this step on ambiguity.

## 4. Flip the status (only after the user has agreed)

Edit the ticket file:

- `- **Status:** open` → `- **Status:** in-progress`
- Don't touch `**Reported:**` — that's the historical record of first observation.

If the user agreed to a paired pickup (e.g., tickets that share a fix surface), flip both files' status in this step.

## 5. Create the branch

Convention: `{domain}/{kebab-case-description}`. See conventions.md § *Branch naming convention* for the domain list.

If the ticket file or INDEX line lists a planned branch name (some teams pre-pick branch names during triage), use that. Otherwise propose one and confirm with the user before creating.

```bash
git status --porcelain
```

If the working tree isn't clean, stop and ask the user what to do with their changes (commit on the current branch first? stash? these are theirs to decide). Don't `git stash` or `git checkout -- .` without explicit permission — those can destroy in-progress work.

Once clean:

```bash
git checkout -b <branch>
```

Branch from whichever default branch the repo uses (`main` or `master` — check with `git symbolic-ref refs/remotes/origin/HEAD` if unsure).

## 6. Move the INDEX line

Open `docs/issues/INDEX.md`. Move the ticket's line from whatever "Open" or "Awaiting input" section it currently lives in into **In progress**. Keep the link target, title, branch annotation, and any pairing note (`— paired with NNNN`).

If the ticket is paired and you flipped both in step 4, move both lines.

## 7. Hand off to companion skills if any exist

This plugin doesn't ship diagnostic skills — those are project-specific. But many projects have skills for:

- UI bug reproduction (Playwright/Cypress-driven login → DOM inspection → API → DB loops)
- Role-based access verification (testing across all user roles)
- Project reference cards (gotchas, ports, demo credentials, known pitfalls)

If skills like that exist in the user's project (`.claude/skills/` or similar), point at them now. Examples of nudges:

- "Touches permission code — if you have a verify-rbac-style skill, run it across all roles before finishing."
- "UI bug — if you have a bug-repro skill for browser-driven testing, use it before editing."
- "Non-trivial — if you have a project-context skill for known gotchas, re-read it now."

Skip the nudges that don't apply. Don't fabricate skill names; only point at ones you actually see in the user's project.

## 8. Report

Tell the user:

- `Started <NNNN> — <title>` (and the paired ticket if any)
- Branch created: `<branch>`
- Ticket status is now `in-progress` and the INDEX is updated
- Plan you both agreed to in step 3 (re-state briefly so they can confirm)
- Any companion skills you flagged for the work ahead

Do not commit. Do not run `git add`. The user reviews diffs themselves.
