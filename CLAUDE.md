# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a **Claude Code plugin marketplace** — a collection of plugins (skills, slash commands, hooks) that users install into Claude Code via the `/plugin` command.

There is no build system, no tests, and no dependencies. The repo is pure Markdown and JSON.

## Repository Structure

```
.claude-plugin/marketplace.json   ← Registry of all plugins (source paths, descriptions)
plugins/<name>/                   ← Each plugin lives in its own directory
  .claude-plugin/plugin.json      ← Plugin metadata (name, description, version)
  skills/<skill>/SKILL.md         ← Skill definitions (frontmatter + instructions)
  README.md                       ← Plugin documentation
```

## How to Add a New Plugin

1. Create `plugins/<name>/`
2. Add `.claude-plugin/plugin.json` with `name`, `description`, and `version`
3. Add skills under `skills/<skill-name>/SKILL.md`
4. Add a `README.md` for the plugin
5. Register the plugin in the root `.claude-plugin/marketplace.json` under the `plugins` array

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
