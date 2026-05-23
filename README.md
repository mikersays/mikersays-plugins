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
| [monograph](plugins/monograph/) | Build a multi-page PhD-level GitHub Pages site on any topic, with research, free-licensed photography, and a topic-tuned design — shipped to `docs/` via parallel expert subagents | `/monograph [topic]` |
| [pr](plugins/pr/) | Create a GitHub PR with auto-generated title, summary, and test plan | `/pr [title]` |
| [plan](plugins/plan/) | Track bugs, features, chores, and todos as markdown in `docs/plan/` | `/plan-init` `/plan-add` `/plan-list` `/plan-update` `/plan-close` |
| [issues](plugins/issues/) | Per-issue bug/feature/incident tracker in `docs/issues/` with symptom/repro/root cause/fix/verification, branch-on-start, and an alignment-before-implement rule | `/issue-init` `/issue-new` `/issue-start` `/issue-close` |
| [maintenance](plugins/maintenance/) | Sync docs, run installer, run uninstaller | `/sync-docs` `/install-marketplace` `/uninstall-marketplace` |

## Contributing

1. Create a directory under `plugins/<name>/`
2. Add `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` (name, description, version; codex also needs `"skills": "./skills/"`)
3. Add your skills under `skills/<skill-name>/SKILL.md`
4. Add a `README.md` for documentation
5. Run `/sync-docs` (from the `maintenance` plugin) to register the plugin across both marketplace files, `INSTALL.md`, `UNINSTALL.md`, and `docs/index.html`
6. Run `python3 scripts/validate.py` to confirm consistency. Enable the pre-commit hook once per clone with `git config core.hooksPath .githooks` so this runs automatically.
