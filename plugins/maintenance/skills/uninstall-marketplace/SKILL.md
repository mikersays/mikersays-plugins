---
name: uninstall-marketplace
description: Run the mikersays-plugins headless uninstaller on this machine and verify everything was removed
allowed-tools: Bash
---

# uninstall-marketplace — Run the Marketplace Uninstaller

Executes the UNINSTALL.md flow on the current machine using `codex exec`. Removes the repo, skill symlinks, marketplace entry, config.toml plugin entries, and the SessionStart hook — without touching anything else.

## Process

### 1. Check prerequisites

```bash
command -v codex || echo "MISSING"
```

If missing, stop and tell the user.

### 2. Confirm intent

Before running, tell the user exactly what will be removed:
- `~/.codex/plugins/mikersays/mikersays-plugins`
- Skill symlinks: `~/.agents/skills/{ship,pr,tech-writer,deck,roadmap,diagram}`
- `mikersays-marketplace` entry from `~/.agents/plugins/marketplace.json`
- 6 plugin entries from `~/.codex/config.toml`
- SessionStart git-pull hook from `~/.codex/hooks.json`

Ask the user to confirm before proceeding (unless `$ARGUMENTS` contains `--yes` or `--force`).

### 3. Run the headless uninstaller

```bash
curl -sL https://raw.githubusercontent.com/mikersays/mikersays-plugins/master/UNINSTALL.md \
  | codex exec --full-auto --add-dir ~/.codex --add-dir ~/.agents --skip-git-repo-check -
```

Capture and display the full output.

### 4. Verify the removal

Run each check and report pass/fail:

```bash
ls ~/.codex/plugins/mikersays 2>/dev/null && echo "STILL PRESENT" || echo "removed"
```
```bash
ls ~/.agents/skills/ship 2>/dev/null && echo "STILL PRESENT" || echo "removed"
```
```bash
python3 -c "
import json, os
path = os.path.expanduser('~/.agents/plugins/marketplace.json')
if not os.path.exists(path):
    print('file gone')
else:
    data = json.load(open(path))
    entries = data if isinstance(data, list) else [data]
    found = any(e.get('name') == 'mikersays-marketplace' for e in entries)
    print('STILL PRESENT' if found else 'removed')
"
```
```bash
grep -c 'mikersays-marketplace' ~/.codex/config.toml 2>/dev/null && echo "STILL PRESENT" || echo "removed"
```
```bash
grep -c 'mikersays' ~/.codex/hooks.json 2>/dev/null && echo "STILL PRESENT" || echo "removed"
```

### 5. Report

Summarize what was removed and confirm nothing else was affected. Note if any items were already absent before the uninstall ran.

## Rules

- Always confirm with the user before running unless `--yes` or `--force` is passed.
- Do not modify any files in this repo.
- If a removal step fails, report it clearly — do not silently continue.
