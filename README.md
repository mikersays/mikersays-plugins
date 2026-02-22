# mikersays-marketplace

A marketplace of Claude Code plugins (skills, slash commands, hooks, and more).

## Install the marketplace

```bash
/plugin marketplace add mikersays/mikersays-marketplace
```

Then install any plugin:

```bash
/plugin install ship@mikersays-marketplace
```

## Plugins

| Plugin | Description | Usage |
|--------|-------------|-------|
| [ship](plugins/ship/) | Git commit and push in one command | `/ship [message]` |
| [tech-writer](plugins/tech-writer/) | Review and rewrite docs using Google's Technical Writing guidelines | `/tech-writer [file path]` |

## Contributing

1. Create a directory under `plugins/<name>/`
2. Add `.claude-plugin/plugin.json` with name, description, and version
3. Add your skills under `skills/<skill-name>/SKILL.md`
4. Add a `README.md` for documentation
5. Register your plugin in `.claude-plugin/marketplace.json`
