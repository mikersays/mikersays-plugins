# mikersays-plugins

A marketplace of plugins for Claude Code and Codex CLI.

## Install — Claude Code

```bash
/plugin marketplace add mikersays/mikersays-plugins
```

Then install any plugin:

```bash
/plugin install ship@mikersays-plugins
```

## Install — Codex CLI

**Headless (one-liner):**

```bash
curl -sL https://raw.githubusercontent.com/mikersays/mikersays-plugins/master/INSTALL.md \
  | codex exec --full-auto --add-dir ~/.codex --add-dir ~/.agents --skip-git-repo-check -
```

**Interactive** — paste this prompt into a Codex session:

```
Read https://raw.githubusercontent.com/mikersays/mikersays-plugins/master/INSTALL.md and follow the instructions exactly to install the mikersays-plugins marketplace on this machine. Create or update the local marketplace file and hooks config, verify the install, and tell me the final result.
```

This clones the repo to `~/.codex/plugins/mikersays/mikersays-plugins`, symlinks skills into `~/.agents/skills/`, registers all plugins in `~/.agents/plugins/marketplace.json`, and installs a `SessionStart` hook that auto-updates the marketplace on every Codex startup.

## Plugins

| Plugin | Description | Usage |
|--------|-------------|-------|
| [ship](plugins/ship/) | Git commit and push in one command | `/ship [message]` |
| [tech-writer](plugins/tech-writer/) | Review and rewrite docs using Google's Technical Writing guidelines | `/tech-writer [file path]` |
| [deck](plugins/deck/) | Generate a self-contained HTML slide deck from a topic | `/deck [topic]` |
| [roadmap](plugins/roadmap/) | Generate a visual HTML Gantt-chart roadmap from a markdown file | `/roadmap [file]` |
| [diagram](plugins/diagram/) | Generate interactive SVG diagrams from a description | `/diagram [description]` |
| [pr](plugins/pr/) | Create a GitHub PR with auto-generated title, summary, and test plan | `/pr [title]` |
| [maintenance](plugins/maintenance/) | Sync docs, run installer, run uninstaller | `/sync-docs` `/install-marketplace` `/uninstall-marketplace` |

## Contributing

1. Create a directory under `plugins/<name>/`
2. Add `.claude-plugin/plugin.json` with name, description, and version
3. Add your skills under `skills/<skill-name>/SKILL.md`
4. Add a `README.md` for documentation
5. Register your plugin in `.claude-plugin/marketplace.json`
