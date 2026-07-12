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

Include `maintenance` in the README table (step 2) and both marketplace registries (steps 6–7); exclude it from INSTALL.md, UNINSTALL.md, and docs/index.html (steps 3–5).

### 2. Update README.md

The repo `README.md` has a markdown table under "## Plugins" with one row per user-facing plugin (everything except `maintenance` — which is listed last as a separate convention). Each row is `[name](plugins/name/) | description | usage`. Add a row for new plugins; remove rows for deleted ones; never reorder existing rows (the order is meaningful — feature plugins first, maintenance last).

### 3. Update INSTALL.md

Add entries for new plugins and delete entries for removed ones in every region that names plugins — do not rewrite existing entries:

- **"Available plugins"** — bullet list of `name — description`
- **Marketplace JSON block (its Step 2)** — a single marketplace object with `plugins[]` entries using `source.source`, `source.path`, `policy.installation`, `policy.authentication`, and `category`. New entries here use `"path": "./.codex/plugins/mikersays/mikersays-plugins/plugins/<name>"` — note the different prefix from the repo registries' `./plugins/<name>` — and default `"policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" }`. Preserve existing entries' hand-tuned `policy`/`category` values here too.
- **Symlink section (its Step 3)** — three plugin-naming regions: a prose sentence enumerating the single-skill plugins, a `for plugin in ...` loop with those same names, and a separate `for skill in ...` loop block per multi-skill plugin (currently `plan` and `issues`). A plugin whose `skills/` directory contains exactly one same-named skill goes into both the prose sentence and the `for plugin in` loop; a multi-skill plugin gets its own commented `for skill in ...` block, with skill names taken from `plugins/<name>/skills/*/`.
- **`config.toml` block (its Step 4b)** — one `[plugins."<name>@mikersays-marketplace"]` entry per plugin for the manual fallback installer

### 4. Update UNINSTALL.md

Mirror the install doc. The skill lists here enumerate every skill symlink — one per skill for multi-skill plugins, one per plugin otherwise, with skill names taken from `plugins/<name>/skills/*/`:

- **"What gets removed"** — comma-separated list of those skill symlink names
- **Unlink loop (its Step 2)** — the same skill names in `for skill in ...`
- **`config.toml` block (its Step 5)** — removal entries per plugin, under both the `@mikersays-plugins` and `@mikersays-marketplace` suffixes

### 5. Update docs/index.html

Find `const PLUGINS = [` in the inline `<script>` and replace only the array contents:

```js
const PLUGINS = [
  { id: '<name>', desc: '<description>' },
  ...
];
```

Leave surrounding JS untouched.

### 6. Add new plugins to .codex-plugin/marketplace.json and .agents/plugins/marketplace.json

Both Codex marketplace files use the same schema. For any plugin missing from either array, append:

```json
{
  "name": "<name>",
  "source": { "source": "local", "path": "./plugins/<name>" },
  "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
  "category": "Productivity"
}
```

Existing entries already have hand-tuned `policy` and `category` values (for example `INSTALLED_BY_DEFAULT`, `ON_USE`, `Developer Tools`, and `Writing`) — preserve them rather than normalizing to the defaults above. Keep both files in sync — they should have identical plugin entries. Current Codex authentication values are `ON_INSTALL` and `ON_USE`; do not use the old `ON_FIRST_USE` spelling.

### 7. Add new plugins to .claude-plugin/marketplace.json

Append missing entries with `name`, `source` (string path), and `description`. Preserve existing entries.

### 8. Verify and report

Read back each changed file, confirm the plugin set matches `plugins/*/`, and report a diff summary (added / removed / files touched). Stop there — leave committing to the user.

## Rules

- The `plugins/` directory is the source of truth. Add an entry when a directory appears; remove an entry only when its directory is gone. Don't reorder existing entries — order is meaningful in the rendered docs.
- Touch only the plugin-list regions named above. Prose, headings, and other JS in `docs/index.html` stay byte-identical.
- Never overwrite hand-tuned `policy` or `category` fields on existing codex entries.
- Existing description text in `README.md`, `INSTALL.md`, and `docs/index.html` is hand-tuned — add entries for new plugins (seeding from the `plugin.json` description) and delete entries for removed plugins, but never rewrite the text of entries that already exist.
- Don't commit. The user reviews the diff before shipping.
