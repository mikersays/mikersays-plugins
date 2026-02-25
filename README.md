# mikersays-plugins

A marketplace of Claude Code plugins (skills, slash commands, hooks, and more).

## Install the marketplace

```bash
/plugin marketplace add mikersays/mikersays-plugins
```

Then install any plugin:

```bash
/plugin install ship@mikersays-plugins
```

## Plugins

| Plugin | Description | Usage |
|--------|-------------|-------|
| [ship](plugins/ship/) | Git commit and push in one command | `/ship [message]` |
| [tech-writer](plugins/tech-writer/) | Review and rewrite docs using Google's Technical Writing guidelines | `/tech-writer [file path]` |
| [deck](plugins/deck/) | Generate a self-contained HTML slide deck from a topic | `/deck [topic]` |
| [roadmap](plugins/roadmap/) | Generate a visual HTML Gantt-chart roadmap from a markdown file | `/roadmap [file]` |
| [diagram](plugins/diagram/) | Generate interactive SVG diagrams from a description | `/diagram [description]` |
| [pr](plugins/pr/) | Create a GitHub PR with auto-generated title, summary, and test plan | `/pr [title]` |

## Contributing

1. Create a directory under `plugins/<name>/`
2. Add `.claude-plugin/plugin.json` with name, description, and version
3. Add your skills under `skills/<skill-name>/SKILL.md`
4. Add a `README.md` for documentation
5. Register your plugin in `.claude-plugin/marketplace.json`
