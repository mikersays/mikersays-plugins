# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a **Claude Code + Codex CLI plugin marketplace** — a collection of plugins (skills, slash commands, hooks) that users install into Claude Code via the `/plugin` command, or into Codex CLI via `codex --install`.

There is no build system, no tests, and no dependencies. The repo is pure Markdown and JSON.

## Repository Structure

```
.claude-plugin/marketplace.json   ← Claude Code registry of all plugins
.codex-plugin/marketplace.json    ← Codex CLI registry of all plugins
plugins/<name>/                   ← Each plugin lives in its own directory
  .claude-plugin/plugin.json      ← Claude Code manifest (name, description, version)
  .codex-plugin/plugin.json       ← Codex CLI manifest (same fields + "skills": "./skills/")
  skills/<skill>/SKILL.md         ← Skill definitions (frontmatter + instructions, shared by both)
  README.md                       ← Plugin documentation
```

## How to Add a New Plugin

1. Create `plugins/<name>/`
2. Add `.claude-plugin/plugin.json` with `name`, `description`, and `version`
3. Add `.codex-plugin/plugin.json` with the same fields plus `"skills": "./skills/"`
4. Add skills under `skills/<skill-name>/SKILL.md`
5. Add a `README.md` for the plugin
6. Register the plugin in both root marketplace files (`plugins` array)

## SKILL.md Format

Skill files use YAML frontmatter followed by Markdown instructions:

- `name` — skill name (used as the slash command)
- `description` — one-line description
- `argument-hint` — placeholder shown to the user (e.g., `"[commit message]"`)
- `disable-model-invocation` — set `true` for tool-only skills
- `allowed-tools` — comma-separated list of tools the skill can use (e.g., `Bash`)

The Markdown body defines the skill's behavior: process steps, rules, and constraints.

## Existing Plugins

- **ship** (`plugins/ship/`) — `/ship [message]` — Git commit and push in one command
- **tech-writer** (`plugins/tech-writer/`) — `/tech-writer [file path]` — Review and rewrite docs using Google's Technical Writing guidelines
- **deck** (`plugins/deck/`) — `/deck [topic]` — Generate a self-contained HTML slide deck
- **roadmap** (`plugins/roadmap/`) — `/roadmap [file]` — Generate a visual HTML Gantt-chart roadmap from a markdown file
- **diagram** (`plugins/diagram/`) — `/diagram [description]` — Generate interactive SVG diagrams from a description
- **pr** (`plugins/pr/`) — `/pr [title]` — Create a GitHub PR with auto-generated title, summary, and test plan
