---
name: handoff
description: >-
  Audit the current session for context that won't survive into a new agent session and help
  the user persist what matters. Use this skill whenever the user says "handoff", "save context",
  "wrap up", "before I go", "new session", "pass the baton", "for next time", "preserve context",
  "what will the next agent know", or anything suggesting they want to capture session knowledge
  before starting fresh. Also trigger when the user asks about what persists between sessions,
  what gets lost, or how to prepare for a handoff to another agent.
allowed-tools: Bash, Read, Write, Edit
---

# Handoff

You are running inside an active session. The user wants to make sure the next agent that opens
this project can pick up where this one left off. Your job is to find the gap between what this
session knows and what the next session will see, then help the user close it.

## How agent sessions work

A new agent session starts with a blank conversation. It sees only what's on disk and in config:

**Persists automatically:**
- CLAUDE.md files in the project tree (loaded into context at session start)
- Memory files in `~/.claude/projects/*/memory/` (loaded when the system deems them relevant)
- Git state: commits, branches, stash, working tree, diffs
- Files on disk: anything written to the filesystem
- Plan docs in `docs/plan/` (if the plan plugin is in use)
- Issue docs in `docs/issues/` (if the issues plugin is in use)

**Lost when this session ends:**
- This entire conversation — every question, answer, and decision
- Reasoning and rationale behind choices made during the session
- Approaches that were tried and rejected, and why they failed
- Debugging insights: root causes found, subtle behaviors observed, error patterns identified
- Mental models built up about the codebase, business logic, or problem domain
- User preferences and working style learned implicitly during the session
- In-flight work that wasn't committed or written to disk
- Environment variables, running processes, and temporary state
- Understanding of external systems, APIs, or dependencies discussed
- Agreements about next steps that weren't tracked anywhere

The next agent is smart but amnesiac. Anything not written down will be re-derived from scratch —
or worse, a different (possibly wrong) conclusion will be reached.

## Process

### Step 1: Audit the persistence layer

Run these checks to see what the next agent will already have:

```bash
# CLAUDE.md files
find . -name "CLAUDE.md" -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null

# Memory directory
ls ~/.claude/projects/*/memory/*.md 2>/dev/null

# Git state
git status --short
git stash list
git log --oneline -5
git diff --stat
git diff --cached --stat

# Plan docs
ls docs/plan/*.md 2>/dev/null

# Issue docs
ls docs/issues/*.md 2>/dev/null
```

Read the CLAUDE.md files and MEMORY.md index (if present) so you know what's already captured.

### Step 2: Reflect on this session

Think through what happened in this session. Be specific — generic summaries are useless.
Scan your memory of the conversation for:

**Decisions and rationale**
What was decided and why? Architectural choices, library picks, API design, naming conventions,
trade-offs weighed. The decision itself might be visible in code, but the *why* is in your head.

**Dead ends**
What was tried and abandoned? Why didn't it work? Without this, the next agent will walk the
same dead-end paths. These are especially expensive to re-derive.

**Debugging insights**
Root causes discovered, non-obvious error patterns, environment quirks, things that look wrong
but are actually intentional. Anything that took real investigation to figure out.

**Implicit user preferences**
How does the user like to work? Do they prefer concise or detailed responses? Do they want to
review before you act, or do they want you to move fast? Any coding style preferences?
Communication patterns you adapted to?

**In-flight work**
Tasks started but not finished. Features partially implemented. Known issues that surfaced
but weren't addressed. Agreed-upon next steps.

**Domain knowledge**
Understanding of business logic, data flows, external system behaviors, or organizational
context that came up during the session and isn't documented anywhere.

### Step 3: Present the analysis

Organize your findings into three sections:

**1. Already persists** — What the next agent will see without any action.
List the specific files and summarize what each contains. Be concrete:
"CLAUDE.md documents the build commands and test approach" not just "CLAUDE.md exists."

**2. Will be lost** — What disappears when this session ends.
List the specific knowledge, decisions, and context from this session.
Each item should be a concrete thing, not a category.

**3. Recommended saves** — What's worth persisting, with a destination for each:

| Context to save | Destination | Reason |
|---|---|---|
| *(specific insight from this session)* | *(where to write it)* | *(what goes wrong without it)* |

Use this destination guide:
- **CLAUDE.md** — Conventions, build/test commands, architectural decisions, constraints that
  affect how any agent should work in this repo. Things that are always relevant.
- **Memory files** — User preferences, recurring project context, feedback on agent behavior,
  pointers to external resources. Things that are relevant when recalled.
- **Git commit message** — If there's uncommitted work, capture the why in the commit message.
  Descriptive commit messages are free context for `git log` and `git blame`.
- **Plan docs** — Work items, next steps, priorities. Only if `docs/plan/` exists or the
  user wants to set it up.
- **Issue docs** — Bug investigations, root causes, reproduction steps. Only if `docs/issues/`
  exists.
- **Code comments** — Non-obvious constraints or workarounds tied to specific code locations.
  Use sparingly — only where the insight is physically bound to the code.

### Step 4: Ask the user

Present the recommended saves and ask the user to confirm. Use the `AskUserQuestion` tool to
let them select which items to persist. Offer the top 3-4 items as options.

If nothing meaningful happened in the session (quick question, trivial fix, exploration with
no findings), say so honestly. Don't manufacture busywork.

If the user says "all of it" or "your call," use your judgment and proceed with the
highest-value items.

### Step 5: Execute the saves

For each item the user approves:

**CLAUDE.md updates:**
Read the existing file. Find the section where the new content belongs, or create an
appropriate section. Append concisely — every word in CLAUDE.md is loaded into every
future session, so it should earn its place. Don't duplicate what's already there.

**Memory files:**
Write to the project memory directory at `~/.claude/projects/*/memory/`.
Use the standard frontmatter format:
```markdown
---
name: short-kebab-slug
description: one-line summary
metadata:
  type: user|feedback|project|reference
---

Content here.
```
Update the MEMORY.md index with a one-line pointer to the new file.

**Git commits:**
If there's uncommitted work, stage the relevant files and commit with a message that
captures the what AND the why. Don't push unless the user asks.

**Plan/issue docs:**
Follow the format conventions of existing docs in those directories. If the directory
doesn't exist, ask before creating the tracking infrastructure.

**Code comments:**
Add inline, one line max. Only for non-obvious constraints or workarounds.

After all saves are complete, give the user a short receipt: what was saved and where.
One line per item.

## Constraints

- Never fabricate context that wasn't part of this session
- Don't save secrets, credentials, tokens, or personal data to files
- Don't push to remote repositories without explicit user approval
- Don't modify code logic — this skill persists knowledge, not changes
- Keep all saves concise — dense context beats verbose transcripts
- If the session was trivial, say "nothing worth persisting" and stop
- Don't create tracking infrastructure (docs/plan/, docs/issues/) without asking first
