---
name: sync-docs
description: Sync INSTALL.md, UNINSTALL.md, and docs/index.html to match the current plugin list in the repo
allowed-tools: Bash, Read, Edit, Glob
---

# sync-docs — Sync Marketplace Documentation

Keep INSTALL.md, UNINSTALL.md, and docs/index.html in sync whenever plugins are added, removed, or renamed.

## Process

### 1. Discover current plugins

Read all plugin manifests to build the authoritative plugin list:

```bash
for dir in plugins/*/; do
  name=$(basename "$dir")
  desc=$(cat "$dir/.claude-plugin/plugin.json" | python3 -c "import sys,json; print(json.load(sys.stdin)['description'])")
  echo "$name|$desc"
done
```

Collect each plugin's `name` and `description`. Ignore the `maintenance` plugin itself.

### 2. Update INSTALL.md

In `INSTALL.md`, update every section that enumerates plugins by name:

- **"Available plugins"** bullet list — regenerate from current plugin list
- **Step 2 marketplace JSON** — regenerate the `"plugins"` array with all current plugin names and their source paths (`../../.codex/plugins/mikersays/mikersays-plugins/plugins/<name>`)
- **Step 3 symlink loop** — update the space-separated plugin list in `for plugin in ...`
- **Step 4b config.toml block** — regenerate all `[plugins."<name>@mikersays-marketplace"]` entries

### 3. Update UNINSTALL.md

In `UNINSTALL.md`, update every section that enumerates plugins:

- **"What gets removed"** skill symlinks bullet — update the comma-separated list
- **Step 2 unlink loop** — update `for skill in ...` to match current plugin list
- **Step 4 config.toml block** — regenerate all `[plugins."<name>@mikersays-marketplace"]` lines to remove

### 4. Update docs/index.html

Find the `const PLUGINS = [` array in the `<script>` block and replace its contents with entries for all current plugins:

```js
const PLUGINS = [
  { id: '<name>', desc: '<description>' },
  ...
];
```

Preserve all surrounding JS — only replace the array literal contents.

### 5. Register new plugins in .codex-plugin/marketplace.json

If any new plugins are not yet in `.codex-plugin/marketplace.json`, add them. Preserve existing entries (including their `policy` and `category` fields). New plugins default to:

```json
{
  "name": "<name>",
  "source": { "source": "local", "path": "./plugins/<name>" },
  "policy": { "installation": "AVAILABLE" },
  "category": "productivity"
}
```

### 6. Register new plugins in .claude-plugin/marketplace.json

If any new plugins are not yet in `.claude-plugin/marketplace.json`, append them with `source` and `description`.

### 7. Verify

- Read back each updated file and confirm plugin names match the discovered list.
- Report a summary: which files were changed and what was added/removed.

## Rules

- Never remove or reorder plugins that are already in the docs — only add new ones or remove ones whose `plugins/<name>/` directory no longer exists.
- Preserve all non-plugin content in INSTALL.md and UNINSTALL.md exactly as-is.
- Preserve all non-PLUGINS-array JS in docs/index.html exactly as-is.
- Do not commit — report the diff and let the user review before shipping.
