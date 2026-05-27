---
name: sync-docs
description: Refresh README.md, INSTALL.md, UNINSTALL.md, docs/index.html, and all three marketplace.json files to match plugins/ on disk
allowed-tools: Bash, Read, Edit, Glob
---

# sync-docs — Sync Marketplace Documentation

Plugin metadata is duplicated across seven files. When you add, remove, or rename a plugin, this skill propagates the change so the docs and registries match the `plugins/` directory.

## Targets

| File | What references plugins |
|---|---|
| `README.md` | Plugins table (one row per user-facing plugin) |
| `INSTALL.md` | "Available plugins" list, marketplace JSON block, symlink loop, `config.toml` block |
| `UNINSTALL.md` | "What gets removed" list, unlink loop, `config.toml` block |
| `docs/index.html` | `const PLUGINS = [...]` array inside `<script>` |
| `.claude-plugin/marketplace.json` | `plugins[]` with `name`, `source`, `description` |
| `.codex-plugin/marketplace.json` | `plugins[]` with `name`, `source`, `policy`, `category` (legacy fallback) |
| `.agents/plugins/marketplace.json` | `plugins[]` with `name`, `source`, `policy`, `category` (canonical Codex path) |

The `maintenance` plugin is its own special case — it stays in the registries and in `README.md` but is omitted from end-user install/uninstall flows and the landing page, since users don't install the maintenance plugin itself.

The two `maintenance` skills `install-marketplace` and `uninstall-marketplace` derive their plugin/skill lists at run time from the cloned repo, so they don't need to be touched by `sync-docs` — they stay correct automatically.

After running, the user should run `python3 scripts/validate.py` (or rely on the pre-commit hook / CI) to confirm consistency.

## Process

### 1. Discover the source of truth

Plugin manifests under `plugins/*/` are authoritative. Read each `plugin.json` to collect `name` and `description`:

```bash
for dir in plugins/*/; do
  name=$(basename "$dir")
  desc=$(python3 -c "import json; print(json.load(open('$dir/.claude-plugin/plugin.json'))['description'])")
  echo "$name|$desc"
done
```

Skip `maintenance` for the install/uninstall doc updates (steps 2–3) but include it for marketplace registries (steps 5–6).

### 2a. Update README.md

The repo `README.md` has a markdown table under "## Plugins" with one row per user-facing plugin (everything except `maintenance` — which is listed last as a separate convention). Each row is `[name](plugins/name/) | description | usage`. Add a row for new plugins; remove rows for deleted ones; never reorder existing rows (the order is meaningful — feature plugins first, maintenance last).

### 2. Update INSTALL.md

Regenerate every section that names plugins:

- **"Available plugins"** — bullet list of `name — description`
- **Marketplace JSON block (Step 2)** — `plugins[]` array with source paths like `../../.codex/plugins/mikersays/mikersays-plugins/plugins/<name>`
- **Symlink loop (Step 3)** — space-separated names in `for plugin in ...`
- **`config.toml` block (Step 4b)** — one `[plugins."<name>@mikersays-marketplace"]` entry per plugin

### 3. Update UNINSTALL.md

Mirror the install doc:

- **"What gets removed"** — comma-separated list of skill symlinks
- **Unlink loop (Step 2)** — names in `for skill in ...`
- **`config.toml` block (Step 4)** — one removal line per plugin

### 4. Update docs/index.html

Find `const PLUGINS = [` in the inline `<script>` and replace only the array contents:

```js
const PLUGINS = [
  { id: '<name>', desc: '<description>' },
  ...
];
```

Leave surrounding JS untouched.

### 5. Add new plugins to .codex-plugin/marketplace.json and .agents/plugins/marketplace.json

Both Codex marketplace files use the same schema. For any plugin missing from either array, append:

```json
{
  "name": "<name>",
  "source": { "source": "local", "path": "./plugins/<name>" },
  "policy": { "installation": "AVAILABLE" },
  "category": "productivity"
}
```

Existing entries already have hand-tuned `policy` and `category` values (e.g. `INSTALLED_BY_DEFAULT`, `developer-tools`) — preserve them rather than normalizing to the defaults above. Keep both files in sync — they should have identical plugin entries.

### 6. Add new plugins to .claude-plugin/marketplace.json

Append missing entries with `name`, `source` (string path), and `description`. Preserve existing entries.

### 7. Verify and report

Read back each changed file, confirm the plugin set matches `plugins/*/`, and report a diff summary (added / removed / files touched). Stop there — leave committing to the user.

## Rules

- The `plugins/` directory is the source of truth. Add an entry when a directory appears; remove an entry only when its directory is gone. Don't reorder existing entries — order is meaningful in the rendered docs.
- Touch only the plugin-list regions named above. Prose, headings, and other JS in `docs/index.html` stay byte-identical.
- Never overwrite hand-tuned `policy` or `category` fields on existing codex entries.
- Don't commit. The user reviews the diff before shipping.
