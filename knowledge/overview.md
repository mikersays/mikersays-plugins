---
type: Reference
title: mikersays-plugins overview
description: What the plugin marketplace is, how it is laid out, and how to add or validate a plugin.
tags: [overview, marketplace]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-10-07T07:53:13Z }
status: draft
sources:
  - id: claude-md
    resource: CLAUDE.md
    title: Repository agent guidance
  - id: readme
    resource: README.md
    title: Repository README
  - id: validate
    resource: scripts/validate.py
    title: Marketplace validator
  - id: hooks
    resource: .codex-plugin/hooks.json
    title: Codex SessionStart hook
---

# What it is

A plugin marketplace for Claude Code and Codex CLI. It holds skills, slash commands, and hooks.[^claude-md] There is no build system, no test suite, and no dependencies: the repository is Markdown, JSON, and YAML, plus stdlib Python scripts.[^claude-md]

* GitHub: `mikersays/mikersays-plugins`. The default branch is `master`.
* Install in Claude Code: `/plugin marketplace add mikersays/mikersays-plugins`, then `/plugin install <plugin>@mikersays-plugins`.[^readme]
* Install in Codex CLI: `codex plugin marketplace add mikersays/mikersays-plugins`, then `codex plugin add <plugin>@mikersays-plugins`.[^readme]
* Codex clones get a `SessionStart` hook that runs `git pull --ff-only` in `~/.codex/plugins/mikersays/mikersays-plugins`.[^hooks]

# Layout

| Path | Role |
|---|---|
| `.claude-plugin/marketplace.json` | Claude Code registry of all plugins |
| `.agents/plugins/marketplace.json` | Codex registry (canonical path) |
| `.codex-plugin/marketplace.json` | Codex registry (legacy fallback) |
| `plugins/<name>/` | One plugin: `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `skills/<skill>/SKILL.md`, optional `agents/openai.yaml`, `README.md` |
| `INSTALL.md`, `UNINSTALL.md` | Codex self-installer and uninstaller |
| `docs/index.html` | Catalog page |
| `CLAUDE.md`, `AGENTS.md` | Instructions for Claude Code and Codex. Keep both. |

# Plugins

`ship`, `tech-writer`, `deck`, `roadmap`, `diagram`, `pr`, `plan`, `issues`, `monograph`, `bootcamp`, `handoff`, `slop`, `gh-pages`, `okf`, and `maintenance`. The `maintenance` plugin (`/sync-docs`, `/install-marketplace`, `/uninstall-marketplace`) is for the marketplace owner and is not installed by end users.[^claude-md]

# Add a plugin

1. Create `plugins/<name>/` with both manifests. The Codex manifest also needs `"skills": "./skills/"` and an `interface` object.
2. Add `skills/<skill>/SKILL.md` with frontmatter whose `name` matches the directory.
3. Add a plugin `README.md`.
4. Run `/sync-docs` to update the three marketplace files, `INSTALL.md`, `UNINSTALL.md`, and `docs/index.html`.
5. Run `python3 scripts/validate.py`.

See [validation](/validation.md) for what the check covers.

[^claude-md]: CLAUDE.md
[^readme]: README.md
[^hooks]: .codex-plugin/hooks.json
