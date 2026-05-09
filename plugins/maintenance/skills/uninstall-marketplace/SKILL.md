---
name: uninstall-marketplace
description: Remove the mikersays-plugins marketplace from this machine via the headless UNINSTALL.md flow, then verify
allowed-tools: Bash
---

# uninstall-marketplace

Pipes `UNINSTALL.md` into `codex exec` to remove the repo, skill symlinks, marketplace entry, `config.toml` plugin entries, and the SessionStart hook. Other marketplaces, skills, and config entries are left untouched — that scoping lives in `UNINSTALL.md` itself, so do not reimplement removal logic here.

## Process

### 1. Check prerequisites

```bash
command -v codex || echo "MISSING"
```

If `codex` is missing, stop and tell the user — the headless flow cannot run without it.

### 2. Confirm intent

Uninstall is destructive and partially irreversible (the repo clone is deleted), so confirm before running. List exactly what will be removed:

- Repo: `~/.codex/plugins/mikersays/mikersays-plugins`
- Skill symlinks in `~/.agents/skills/`: `ship`, `pr`, `tech-writer`, `deck`, `roadmap`, `diagram`
- `mikersays-marketplace` entry in `~/.agents/plugins/marketplace.json`
- 6 `mikersays-marketplace` plugin entries in `~/.codex/config.toml`
- SessionStart git-pull hook in `~/.codex/hooks.json`

Skip the confirmation prompt if `$ARGUMENTS` contains `--yes` or `--force`.

### 3. Run the headless uninstaller

```bash
curl -sL https://raw.githubusercontent.com/mikersays/mikersays-plugins/master/UNINSTALL.md \
  | codex exec --full-auto --add-dir ~/.codex --add-dir ~/.agents --skip-git-repo-check -
```

`--add-dir` is scoped to the two directories the uninstaller writes to, so a misbehaving step cannot reach anywhere else. Capture and surface the full output — the user needs to see what each step did.

### 4. Verify

Run each check and report pass/fail. Items already absent before the run count as pass — uninstall is idempotent.

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

Summarize what was removed, flag anything that was already absent, and surface any failed step verbatim. Do not retry or paper over a failure — the user may have a customized config that needs manual handling.

## Constraints

- Do not modify files in this repo. The skill operates on the user's machine state, not the marketplace source.
- Do not invent additional removal steps. If `UNINSTALL.md` does not remove something, neither does this skill.
