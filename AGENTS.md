# AGENTS.md

This file provides guidance to Codex CLI when working with code in this repository.

## Overview

This is a **Claude Code + Codex CLI plugin marketplace** — a collection of plugins (skills, slash commands, hooks) that users install into Claude Code via the `/plugin` command, or into Codex CLI via `codex plugin marketplace add`.

There is no build system, no tests, and no dependencies. The repo is pure Markdown, JSON, and YAML.

## Repository Structure

```
.agents/plugins/marketplace.json  <- Codex CLI registry (canonical path)
.claude-plugin/marketplace.json   <- Claude Code registry
.codex-plugin/marketplace.json    <- Codex CLI registry (legacy fallback)
.codex-plugin/hooks.json          <- SessionStart hook config (git pull on startup)
CLAUDE.md                         <- Claude Code project instructions
AGENTS.md                         <- Codex CLI project instructions
INSTALL.md                        <- Codex self-installer (give to a Codex agent to run)
plugins/<name>/                   <- Each plugin lives in its own directory
  .claude-plugin/plugin.json      <- Claude Code manifest (name, description, version)
  .codex-plugin/plugin.json       <- Codex CLI manifest (same fields + skills, interface)
  skills/<skill>/SKILL.md         <- Skill definitions (frontmatter + instructions)
  skills/<skill>/agents/openai.yaml <- Codex skill UI metadata (optional)
  README.md                       <- Plugin documentation
```

## How to Add a New Plugin

1. Create `plugins/<name>/`
2. Add `.claude-plugin/plugin.json` with `name`, `description`, and `version`
3. Add `.codex-plugin/plugin.json` with the same fields plus `"skills": "./skills/"` and an `interface` object (`displayName`, `shortDescription`, `category`)
4. Add skills under `skills/<skill-name>/SKILL.md`
5. Optionally add `skills/<skill-name>/agents/openai.yaml` for Codex UI metadata
6. Add a `README.md` for the plugin
7. Run `/sync-docs` to propagate the new plugin into all three marketplace files, `INSTALL.md`, `UNINSTALL.md`, and `docs/index.html`. (Doing it by hand also works — `/sync-docs` just automates it.)
8. Run `python3 scripts/validate.py` to confirm everything stayed consistent. The pre-commit hook and CI run the same check.

## Validation

`scripts/validate.py` is the source of truth for marketplace consistency. It runs on every push and PR via `.github/workflows/validate.yml`, and locally via `.githooks/pre-commit`.

The validator checks:
- All three marketplace JSON files parse and contain every `plugins/<name>/` directory
- Both `CLAUDE.md` and `AGENTS.md` exist at the repo root
- Every `plugins/<name>/` has both `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` with matching `name` fields
- Every `.codex-plugin/plugin.json` has an `interface` object
- Every `SKILL.md` has parseable frontmatter with `name` matching its directory
- Every `agents/openai.yaml` (if present) has an `interface:` key and is non-empty
- Every user-facing plugin and skill (everything except `maintenance`) appears in `INSTALL.md`, `UNINSTALL.md`, and `docs/index.html`

## SKILL.md Format

Skill files use YAML frontmatter followed by Markdown instructions:

- `name` — skill name (used as the slash command)
- `description` — one-line description (used for implicit skill matching in Codex)

Claude Code also recognizes these optional fields (ignored by Codex):
- `argument-hint` — placeholder shown to the user
- `disable-model-invocation` — set `true` for tool-only skills
- `allowed-tools` — comma-separated list of tools the skill can use

## Existing Plugins

- **ship** (`plugins/ship/`) — `/ship [message]` — Git commit and push in one command
- **tech-writer** (`plugins/tech-writer/`) — `/tech-writer [file path]`, `/ste [file path]` — Review and rewrite docs using Google's Technical Writing guidelines (extended with clarity rules adapted from ASD-STE100), or convert them to strict Simplified Technical English with `/ste`
- **deck** (`plugins/deck/`) — `/deck [topic]` — Generate a self-contained HTML slide deck
- **roadmap** (`plugins/roadmap/`) — `/roadmap [file]` — Generate a visual HTML Gantt-chart roadmap from a markdown file
- **diagram** (`plugins/diagram/`) — `/diagram [description]` — Generate interactive SVG diagrams from a description
- **pr** (`plugins/pr/`) — `/pr [title]` — Create a GitHub PR with auto-generated title, summary, and test plan
- **plan** (`plugins/plan/`) — `/plan-init`, `/plan-add`, `/plan-list`, `/plan-update`, `/plan-close` — Lightweight markdown tracker for bugs/features/chores/todos in `docs/plan/`
- **issues** (`plugins/issues/`) — `/issue-init`, `/issue-new`, `/issue-start`, `/issue-close` — Per-issue bug/feature/incident tracker in `docs/issues/` with symptom/repro/root cause/fix/verification, branch-on-start, and an alignment-before-implement rule
- **handoff** (`plugins/handoff/`) — `/handoff` — Audit session context and persist what matters for the next agent
- **monograph** (`plugins/monograph/`) — `/monograph [topic]` — Build a multi-page PhD-level GitHub Pages site
- **bootcamp** (`plugins/bootcamp/`) — `/bootcamp [topic]` — Swarm of expert subagents builds an interactive zero-to-hero course site (modules, exercises, quizzes, capstone, progress tracking) into `docs/` and deploys it on GitHub Pages
- **slop** (`plugins/slop/`) — `/slop [file | text | topic]` — Rewrite any text to maximally overuse every known AI-writing tell
- **gh-pages** (`plugins/gh-pages/`) — `/gh-pages [site description]` — Build or publish a static site on GitHub Pages: saves the site to `docs/` and enables Pages from the `docs/` folder on the default branch
- **maintenance** (`plugins/maintenance/`) — `/sync-docs`, `/install-marketplace`, `/uninstall-marketplace` — Marketplace maintenance skills; not installed by end users
