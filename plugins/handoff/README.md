# handoff

Capture session context before it disappears.

## Usage

```
/handoff
```

Invoke mid-session when you're about to wrap up or switch to a new agent. The skill audits what the next agent will and won't see, identifies valuable context from the current session, and helps you persist it to the right place.

## What it does

1. **Audits persistence** — scans for CLAUDE.md files, memory files, git state, plan/issue docs
2. **Reflects on the session** — identifies decisions, rejected approaches, debugging insights, user preferences, and in-flight work from the current conversation
3. **Categorizes context** — separates what already persists from what will be lost
4. **Recommends saves** — suggests what to capture and where (CLAUDE.md, memory, git commit, plan docs)
5. **Asks the user** — confirms which items to persist before writing anything
6. **Executes** — writes to the appropriate locations and gives a receipt

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
