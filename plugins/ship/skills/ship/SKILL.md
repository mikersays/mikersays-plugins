---
name: ship
description: Stage, commit, and push all changes in one step, with auto-generated message if none given
argument-hint: "[commit message]"
disable-model-invocation: true
allowed-tools: Bash
---

# Ship

Stage all changes, commit, and push to the remote in one shot. If `$ARGUMENTS` is empty, the script generates a timestamped message.

## Run

Invoke the bundled script, forwarding `$ARGUMENTS` as the commit message. The script lives inside the installed plugin tree — under `~/.claude/plugins` (Claude Code) or `~/.codex/plugins` (Codex CLI) — so search both (not the current working directory):

```bash
bash "$(find ~/.claude/plugins ~/.codex/plugins -path '*/ship/scripts/ship.sh' -print -quit 2>/dev/null)" "$ARGUMENTS"
```

If `$ARGUMENTS` is empty, drop the final `"$ARGUMENTS"` argument and run the script with none, so it generates the timestamped message.

If `find` returns nothing (plugin not installed in the expected location), report the error and stop — do not retry.

Then surface the script's output to the user.

The script handles: repo check, clean-tree early exit, `git add -A`, commit (with provided or timestamped message), and push (setting upstream on first push).

## Constraints

These rules exist because shipping is fast and irreversible — the safeguards keep that speed from turning destructive.

- No force pushes. They rewrite remote history and can erase teammates' work.
- No `--no-verify`. Pre-commit hooks exist for a reason; bypassing them ships broken code.
- On push, auth, conflict, or any non-hook failure: report the error verbatim and stop. Retrying blindly hides the real problem.
- Exception — pre-commit hook failure: fix the underlying issue, then re-run the script (it re-stages and creates a fresh commit). Don't amend — the failed commit was never created, so amending would rewrite the *previous* commit and risk losing earlier work.
