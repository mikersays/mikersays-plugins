---
name: install-marketplace
description: Run the mikersays-plugins headless installer on this machine and verify the result
allowed-tools: Bash
---

# install-marketplace — Run the Marketplace Installer

Executes the INSTALL.md flow on the current machine using `codex exec`. Use this to do a fresh install, test that the installer works after changes, or recover a broken install.

## Process

### 1. Check prerequisites

```bash
command -v codex || echo "MISSING"
command -v git   || echo "MISSING"
```

If either is missing, stop and tell the user what to install.

### 2. Run the headless installer

```bash
curl -sL https://raw.githubusercontent.com/mikersays/mikersays-plugins/master/INSTALL.md \
  | codex exec --full-auto --add-dir ~/.codex --add-dir ~/.agents --skip-git-repo-check -
```

Capture and display the full output.

### 3. Verify the install

Run each check and report pass/fail:

```bash
ls ~/.codex/plugins/mikersays/mikersays-plugins/.codex-plugin/marketplace.json
```
```bash
python3 -c "
import json
data = json.load(open('$HOME/.agents/plugins/marketplace.json'))
entries = data if isinstance(data, list) else [data]
found = any(e.get('name') == 'mikersays-marketplace' for e in entries)
print('FOUND' if found else 'MISSING')
"
```
```bash
grep -c 'mikersays-marketplace' ~/.codex/config.toml && echo "config entries present"
```
```bash
ls ~/.agents/skills/ship ~/.agents/skills/pr ~/.agents/skills/tech-writer \
   ~/.agents/skills/deck ~/.agents/skills/roadmap ~/.agents/skills/diagram
```
```bash
git -C ~/.codex/plugins/mikersays/mikersays-plugins log --oneline -1
```

### 4. Report

Summarize: what was already installed (skipped), what was newly installed, and any failures. Show the installed commit hash.

## Rules

- Do not modify any files in this repo — only run the installer against `~/.codex` and `~/.agents`.
- If the installer fails partway through, report exactly which step failed and what the error was.
- Do not retry blindly — diagnose first.
