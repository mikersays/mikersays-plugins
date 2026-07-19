---
name: install-marketplace
description: Run the mikersays-plugins native Codex installer on this machine and verify the result
disable-model-invocation: true
allowed-tools: Bash
---

# install-marketplace

Run the canonical native Codex plugin flow to do a fresh install, validate installer changes, or recover a broken setup. The installer writes Codex marketplace and plugin state under `~/.codex`.

## 1. Check prerequisites

```bash
command -v codex || echo "MISSING"
```

If `codex` is missing, stop and tell the user to install it. The rest of the flow needs the CLI.

## 2. Add the marketplace

Use the native Codex marketplace command:

```bash
codex plugin marketplace add mikersays/mikersays-plugins
```

Show the full output. If the marketplace is already present, report that and continue.

## 3. Install plugins

Install each user-facing plugin from the marketplace:

```bash
for plugin in ship pr tech-writer deck roadmap diagram monograph bootcamp plan issues handoff slop gh-pages; do
  codex plugin add "$plugin@mikersays-plugins"
done
```

Show the full output. If a plugin is already installed, report that and continue.

## 4. Verify

Run each check and report pass/fail individually. Partial failure is informative; a single combined check would hide which step broke.

```bash
codex plugin marketplace list
```
```bash
codex plugin list
```
```bash
grep -c 'mikersays-plugins' ~/.codex/config.toml && echo "config entries present"
```
```bash
grep -E '^\[plugins\."(ship|pr|tech-writer|deck|roadmap|diagram|monograph|bootcamp|plan|issues|handoff|slop|gh-pages)@mikersays-plugins"\]' ~/.codex/config.toml
```

## 5. Report

Summarize what was newly installed, what was skipped (already present), and any failures with the exact error.

## Constraints

- Don't touch this repo's working tree — the installer only writes Codex state under `~/.codex`.
- If a step fails, diagnose before retrying. Blind retries usually re-trigger the same failure and obscure the cause.
