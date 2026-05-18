# Plan item schema

Every item in `docs/plan/` is a single markdown file named `NNN-kebab-slug.md` (3-digit zero-padded ID + slug from the title). The file has YAML frontmatter followed by a free-form markdown body.

```markdown
---
id: 042
title: Add search to docs site
type: feature
status: open
priority: med
due: 2026-06-01
tags: [docs, search]
created: 2026-05-18
updated: 2026-05-18
closed:
---

A short paragraph describing what needs to happen and why.

## Notes

Anything else: links, repro steps, design sketches.
```

## Field reference

| Field | Required | Values | Notes |
|---|---|---|---|
| `id` | yes | `NNN` (3-digit zero-padded) | Matches the filename prefix. Never changes after creation. |
| `title` | yes | string | Human-readable headline. Used to derive the slug. |
| `type` | yes | `bug` \| `feature` \| `chore` \| `todo` | Default: `todo` when unclear. |
| `status` | yes | `open` \| `in-progress` \| `blocked` \| `done` | Default: `open` on new items. |
| `priority` | yes | `high` \| `med` \| `low` | Default: `med`. |
| `due` | no | ISO date `YYYY-MM-DD` | Omit the line entirely when there's no deadline. |
| `tags` | no | YAML flat list, e.g. `[a, b]` | Lowercase, hyphenated. |
| `created` | yes | ISO date | Set once by `/plan-add`. Never edited. |
| `updated` | yes | ISO date | Bumped on every write. |
| `closed` | no | ISO date | Set by `/plan-close`. Present iff `status: done`. |

## Semantics

**Status**
- `open` — not yet started.
- `in-progress` — actively being worked on.
- `blocked` — waiting on something external. The body should explain what.
- `done` — completed or abandoned (reason in body). `closed` gets stamped the same day.

**Type**
- `bug` — something is broken or behaves wrong.
- `feature` — new capability or enhancement.
- `chore` — maintenance, refactor, deps, docs upkeep.
- `todo` — anything else: research, decisions, follow-ups.

**Priority**
- `high` — affects work imminently; do soon.
- `med` — should happen but not urgent. Default for new items.
- `low` — nice-to-have; can sit indefinitely.

## What's deliberately not here

- No `assignee` — solo / local-first tracker. Use git blame for "who last touched".
- No `created/updated` timestamps with minute precision — date-only is plenty for planning.
- No `severity` or `subsystem` — use `tags:` if you need more axes.
- No `scheduled` (start date) separate from `due` — adopt only if you find yourself wanting it.
