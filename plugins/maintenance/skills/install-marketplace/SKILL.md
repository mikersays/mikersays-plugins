---
name: install-marketplace
description: Run the mikersays-plugins headless installer on this machine and verify the result
disable-model-invocation: true
allowed-tools: Bash
---

# install-marketplace

Run the canonical `INSTALL.md` flow via `codex exec` to do a fresh install, validate installer changes, or recover a broken setup. The installer writes only to `~/.codex` and `~/.agents`.

## 1. Check prerequisites

```bash
command -v codex || echo "MISSING"
command -v git   || echo "MISSING"
```

If either is missing, stop and tell the user to install it. The rest of the flow needs both.

## 2. Run the headless installer

Pipe `INSTALL.md` directly into `codex exec`. The `--add-dir` flags scope write access to the two install directories so no broader sandbox escalation is required.

If you are running inside a checkout of this repo (an `INSTALL.md` exists at the git toplevel), use the local file — that is the only way local installer edits actually get exercised:

```bash
codex exec --full-auto --add-dir ~/.codex --add-dir ~/.agents --skip-git-repo-check - \
  < "$(git rev-parse --show-toplevel)/INSTALL.md"
```

Otherwise fetch from GitHub master. `-f` plus the guard prevents a 404 or network error from feeding an error page to the `--full-auto` agent as its prompt:

```bash
tmp=$(mktemp)
curl -fsSL https://raw.githubusercontent.com/mikersays/mikersays-plugins/master/INSTALL.md > "$tmp" \
  || { echo "INSTALL.md fetch failed — stopping"; exit 1; }
codex exec --full-auto --add-dir ~/.codex --add-dir ~/.agents --skip-git-repo-check - < "$tmp"
```

Show the full output — the user wants to see what the installer did.

## 3. Verify

Run each check and report pass/fail individually. Partial failure is informative; a single combined check would hide which step broke. The skill list is derived at run time from the cloned repo, so it stays correct as plugins are added or removed.

```bash
ls ~/.codex/plugins/mikersays/mikersays-plugins/.agents/plugins/marketplace.json
```
```bash
python3 -c "
import json, os, sys
p = os.path.expanduser('~/.agents/plugins/marketplace.json')
if not os.path.exists(p):
    print('MISSING'); sys.exit()
data = json.load(open(p))
entries = data if isinstance(data, list) else [data]
found = any(e.get('name') == 'mikersays-marketplace' for e in entries)
print('FOUND' if found else 'MISSING')
"
```
```bash
grep -c 'mikersays-marketplace' ~/.codex/config.toml && echo "config entries present"
```
```bash
# Discover expected skills from the freshly cloned repo, then check each symlink.
# The maintenance plugin is excluded: INSTALL.md intentionally never symlinks its skills.
REPO=~/.codex/plugins/mikersays/mikersays-plugins
expected=$(find "$REPO/plugins" -mindepth 3 -maxdepth 3 -type d -path '*/skills/*' -not -path '*/plugins/maintenance/*' -exec basename {} \; | sort)
missing=0
for skill in $expected; do
  if [ -L "$HOME/.agents/skills/$skill" ] || [ -e "$HOME/.agents/skills/$skill" ]; then
    echo "✓ $skill"
  else
    echo "✗ $skill MISSING"
    missing=$((missing + 1))
  fi
done
[ "$missing" -eq 0 ] && echo "All skill symlinks present" || echo "$missing skill symlink(s) missing"
```
```bash
git -C ~/.codex/plugins/mikersays/mikersays-plugins log --oneline -1
```

## 4. Report

Summarize what was newly installed, what was skipped (already present), any failures with the exact error, and the installed commit hash.

## Constraints

- Don't touch this repo's working tree — the installer only writes to `~/.codex` and `~/.agents`.
- If a step fails, diagnose before retrying. Blind retries usually re-trigger the same failure and obscure the cause.
