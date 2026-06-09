---
name: handoff
description: >-
  Audit the current session for context that won't survive into a new agent session and help
  the user persist what matters. Use this skill whenever the user says "handoff", "persist", "persist
  context", "save context", "wrap up", "before I go", "new session", "pass the baton", "for next time",
  "preserve context", "prepare for the next agent", "what will the next agent know", or anything
  suggesting they want to capture session knowledge before starting fresh. Also trigger when the user
  asks about what persists between sessions, what gets lost, or how to prepare a handoff to another agent.
allowed-tools: Bash, Read, Write, Edit
---

# Handoff

You are running inside an active session. The user wants the next agent that opens this project to
pick up where this one left off, instead of re-deriving everything from scratch. Your job is to find
the gap between what this session knows and what the next session will actually see on disk, then
help close it.

This is a judgment task, not a checklist. The sections below give you a mental model and a set of
options — use them to reason about *this* session and *this* repo, not to march through fixed steps.
A trivial session deserves a one-line "nothing worth persisting." A session full of hard-won
decisions deserves real care. Match the effort to what actually happened.

## Know which agent you are

This skill runs in two different harnesses, and the persistence targets differ between them. Figure
out which one you're in before you do anything else — you already know your own harness, but confirm
against what's on disk:

- **Claude Code** — the always-loaded project-instructions file is `CLAUDE.md`. Memory files live at
  `~/.claude/projects/*/memory/` with a `MEMORY.md` index, and are recalled when relevant.
- **Codex CLI** — the always-loaded project-instructions file is `AGENTS.md`. There is **no memory-file
  system**; anything you'd otherwise route to a memory file goes into `AGENTS.md` or the repo's own docs
  instead.

Throughout the rest of this skill, wherever it says "the project-instructions file," use `CLAUDE.md`
in Claude Code and `AGENTS.md` in Codex. Some repos keep both (this marketplace does) — write to the
one your harness loads, and only touch the other if the user asks. When in doubt, prefer the file that
already exists in the repo root.

## What survives, and what doesn't

A new agent session starts with a blank conversation. It sees only what's on disk and in config —
never the conversation you and the user just had.

**Survives automatically** (anything written to the filesystem or git):
the project-instructions file loaded at session start (`CLAUDE.md` in Claude Code, `AGENTS.md` in
Codex), memory files recalled when relevant (Claude Code only), git state (commits, branches, stash,
diffs), and any docs the project keeps. *Which* of these a repo actually uses varies — that's
something to discover, not assume.

**Lost when this session ends:**
the conversation itself, and everything that lived only in it — the *why* behind decisions,
approaches tried and abandoned, debugging insights and root causes, mental models of the codebase
or domain, user preferences you picked up implicitly, in-flight work not yet written down, and
agreed next steps tracked nowhere.

The next agent is smart but amnesiac. Whatever isn't written down gets re-derived from scratch —
or worse, re-derived *differently*, reaching a conclusion that contradicts what was settled here.
The expensive things to lose are the ones that took real work to figure out: a dead end that looked
promising, a root cause buried three layers deep, a constraint the user mentioned once in passing.

## How to approach it

### See what the next agent already has

Before deciding what to save, look at what already persists, so you don't duplicate it and you know
where new context belongs. Tailor the look to the repo — these are starting points, not a fixed
script:

```bash
# project-instructions files — CLAUDE.md (Claude Code) and/or AGENTS.md (Codex)
find . \( -name "CLAUDE.md" -o -name "AGENTS.md" \) -not -path "*/node_modules/*" -not -path "*/.git/*" 2>/dev/null
ls ~/.claude/projects/*/memory/*.md 2>/dev/null   # Claude Code only: memory files + MEMORY.md index
git status --short && git stash list && git log --oneline -5 && git diff --stat
```

Then read what you found, and notice how *this* repo keeps knowledge. Does it have a `docs/plan/`
or `docs/issues/` tree? A `decisions/` or ADR folder? A `NOTES.md`? Rich commit messages? Whatever
conventions already exist are where new context should go — route to the repo's own habits rather
than imposing a structure it doesn't use.

### Reflect on what this session actually produced

Replay the session and pull out the things that won't survive but should. The categories worth
scanning for: **decisions and their rationale**, **dead ends** (what was tried, why it failed),
**debugging insights** (root causes, quirks, things that look wrong but are intentional), **implicit
user preferences** (pace, review style, conventions you adapted to), **in-flight work** (started,
not finished; agreed next steps), and **domain knowledge** (business logic, data flows, external
system behavior that came up and isn't written anywhere).

Be concrete and honest. "Refactored the auth flow" is useless; "switched to short-lived JWTs because
the session store couldn't handle the concurrent-login case — Redis approach was tried first and
abandoned, see why below" is gold. And if the session was a quick question or a trivial fix with
nothing hard-won in it, the right answer is to say so and stop. Don't manufacture busywork.

### Show the user, then let them steer

Tell the user briefly what already persists, what's about to be lost, and what you'd recommend
saving — each recommendation paired with *where* it should go and *what breaks* without it. Keep
this proportional: a couple of lines for a light session, a short table for a heavy one. The format
is yours to choose; clarity matters more than any fixed template.

Then let the user decide. For a handful of distinct items, `AskUserQuestion` makes selection easy,
but it's a tool, not a requirement — a plain "want all of these, or a subset?" is often enough. If
they say "your call," use judgment and save the highest-value items.

### Write each save where it belongs

Match the destination to the kind of knowledge:

| Destination | Best for | Watch out for |
|---|---|---|
| **The project-instructions file** (`CLAUDE.md` in Claude Code, `AGENTS.md` in Codex) | Conventions, build/test commands, architecture decisions, constraints that affect *any* agent, always | Every word loads into every future session — keep it dense, don't duplicate what's there. Write to the file your harness loads |
| **Memory files** (`~/.claude/projects/*/memory/`) — *Claude Code only* | User preferences, recurring project context, behavior feedback, pointers to external resources — recalled when relevant | Use the standard frontmatter; add a one-line pointer to MEMORY.md. In Codex there are no memory files — route this kind of context into `AGENTS.md` (or the repo's docs) instead |
| **Git commit message** | The *why* behind uncommitted work | Capture what + why; don't push unless asked |
| **The repo's own tracking docs** (plan/issues/ADR/notes, *if present*) | Work items, next steps, bug investigations, decision records | Follow existing format; don't create new tracking infrastructure without asking |
| **Code comments** | Non-obvious constraints tied to a specific line | One line, sparingly — only where the insight is physically bound to the code |

Memory file frontmatter, when you use it (Claude Code only):
```markdown
---
name: short-kebab-slug
description: one-line summary
metadata:
  type: user|feedback|project|reference
---

Content here.
```

When the saves are done, give a short receipt — one line per item: what was saved and where.

## Guardrails

A few things to hold firm on, because they're easy to get wrong and costly when you do:

- **Don't fabricate.** Only persist context that genuinely came from this session. An invented
  rationale is worse than a missing one — the next agent will trust it.
- **Don't leak secrets.** Keep credentials, tokens, and personal data out of any file you write.
- **This skill persists knowledge, not code changes.** Don't alter program logic, and don't push to
  a remote, unless the user explicitly asks.
