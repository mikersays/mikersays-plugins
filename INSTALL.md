# mikersays-plugins — Codex Native Install

This page installs the mikersays plugin marketplace with Codex's native plugin commands.

## What this sets up

Adds the GitHub marketplace:

```bash
codex plugin marketplace add mikersays/mikersays-plugins
```

Then installs plugins from that marketplace using:

```bash
codex plugin add <plugin>@mikersays-plugins
```

## Available plugins

- `ship` — Stage, commit, and push all changes in one step, with auto-generated message if none given
- `pr` — Create a GitHub PR for the current branch with auto-generated title, summary, and test plan
- `tech-writer` — Review and rewrite documentation in place using Google's Technical Writing guidelines
- `deck` — Generate a self-contained HTML slide deck from a topic — single file, dark theme, keyboard nav
- `roadmap` — Generate a self-contained interactive HTML Gantt chart from a markdown roadmap file
- `diagram` — Generate an interactive SVG diagram (architecture, sequence, flowchart, ER) from a description
- `monograph` — Build a multi-page PhD-level GitHub Pages site on any topic — research, free-licensed photography, a distinctive topic-tuned design, all built by a team of parallel expert subagents and shipped to docs/
- `bootcamp` — Spin up a swarm of expert subagents to build an interactive zero-to-hero course site on any topic — progressive modules, worked examples, exercises with solutions, checkpoints, a capstone, and progress tracking — shipped to docs/ and deployed on GitHub Pages
- `plan` — Lightweight markdown-based tracker for bugs/features/chores/todos that lives in docs/plan/ inside your repo; includes `plan-init`, `plan-add`, `plan-list`, `plan-update`, and `plan-close`
- `issues` — Per-issue bug/feature/incident tracker in docs/issues/ — one file per ticket with symptom/repro/root cause/fix/verification, branch-on-start, and a hard rule to align with the user before implementing; includes `issue-init`, `issue-new`, `issue-start`, and `issue-close`
- `handoff` — Audit session context and persist what matters for the next agent — decisions, dead ends, insights, and in-flight work
- `slop` — Rewrite any text to maximally overuse every known AI-writing tell — em-dashes, the rule of three, "not X but Y", and the rest
- `gh-pages` — Build or publish a static site on GitHub Pages — saves the site to docs/ and enables Pages from the docs/ folder on the default branch

## Install

First add the marketplace:

```bash
codex plugin marketplace add mikersays/mikersays-plugins
```

Then install one or more plugins:

```bash
codex plugin add ship@mikersays-plugins
codex plugin add pr@mikersays-plugins
codex plugin add tech-writer@mikersays-plugins
```

Repeat `codex plugin add <plugin>@mikersays-plugins` for any plugin listed above.

## Prompt to give Codex

```
Read @INSTALL.md and use Codex's native plugin commands to add the mikersays/mikersays-plugins marketplace. Then install the requested plugins with codex plugin add <plugin>@mikersays-plugins and report the final result.
```
