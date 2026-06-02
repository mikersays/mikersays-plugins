# handoff

Capture session context before it disappears.

## Usage

```
/handoff
```

Invoke mid-session when you're about to wrap up or switch to a new agent. The skill audits what the next agent will and won't see, identifies valuable context from the current session, and helps you persist it to the right place.

## What it does

It treats the handoff as a judgment call, not a fixed checklist, and scales the effort to what the session actually produced:

1. **Sees what already persists** — checks CLAUDE.md, memory files, git state, and whatever tracking docs the repo actually keeps, so it doesn't duplicate existing context
2. **Reflects on the session** — pulls out decisions and their rationale, rejected approaches, debugging insights, implicit user preferences, and in-flight work from the conversation
3. **Recommends saves** — shows what's about to be lost and where each piece should go, routing to the repo's own conventions rather than imposing new structure
4. **Lets the user steer** — confirms what to persist (and skips the ceremony when the session was trivial)
5. **Writes and reports back** — saves to the right locations and gives a one-line-per-item receipt

## Why

Agent sessions are ephemeral. The conversation, reasoning, and mental models built during a session vanish when it ends. The next agent starts fresh — smart but amnesiac. Without a deliberate handoff, it will re-derive decisions from scratch, walk dead-end paths you already explored, and miss context that took real work to build up.

## Save destinations

| Destination | Best for |
|---|---|
| CLAUDE.md | Conventions, architecture decisions, constraints — always loaded |
| Memory files | User preferences, project context, feedback — loaded when relevant |
| Git commit messages | The "why" behind code changes — visible via `git log` |
| Plan docs | Work items, next steps, priorities |
| Issue docs | Bug investigations, root causes, reproduction steps |
| Code comments | Non-obvious constraints tied to specific code |
