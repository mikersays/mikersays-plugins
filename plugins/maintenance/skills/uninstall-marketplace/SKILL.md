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

Uninstall is destructive and partially irreversible (the repo clone is deleted), so confirm before running. Inspect the current install state and list exactly what's about to disappear — derive the lists at runtime so this stays correct no matter how the marketplace evolves:

```bash
# Skill symlinks pointing into our marketplace
echo "Skill symlinks to remove from ~/.agents/skills/:"
for s in "$HOME/.agents/skills"/*; do
  [ -L "$s" ] || continue
  target=$(readlink "$s")
  case "$target" in
    *mikersays-plugins*) echo "  - $(basename "$s")" ;;
  esac
done

# config.toml plugin entries
echo ""
echo "config.toml plugin entries to remove:"
grep -E '^\[plugins\."[^"]+@mikersays-marketplace"\]' ~/.codex/config.toml 2>/dev/null \
  | sed 's/^/  - /' || echo "  (none — config.toml absent or no entries)"
```

Also fixed:

- Repo: `~/.codex/plugins/mikersays/mikersays-plugins`
- `mikersays-marketplace` entry in `~/.agents/plugins/marketplace.json`
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
# Any symlink in ~/.agents/skills/ still pointing at our marketplace?
leftover=0
for s in "$HOME/.agents/skills"/*; do
  [ -L "$s" ] || continue
  target=$(readlink "$s")
  case "$target" in
    *mikersays-plugins*) echo "STILL PRESENT: $(basename "$s")"; leftover=$((leftover + 1)) ;;
  esac
done
[ "$leftover" -eq 0 ] && echo "removed (no mikersays symlinks remain)"
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
