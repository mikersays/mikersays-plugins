---
name: ship
description: Git commit and push current changes in one step
argument-hint: "[commit message]"
disable-model-invocation: true
allowed-tools: Bash
---

# Ship — Commit and Push

Commit all staged and unstaged changes, then push to the remote.

## Process

Run the bundled script, passing `$ARGUMENTS` as the commit message:

```bash
bash "$(dirname "$(find . -path '*/ship/scripts/ship.sh' -print -quit 2>/dev/null || echo /dev/null)")/ship.sh" $ARGUMENTS
```

If the script is not found at a known path, fall back to running it directly:

```bash
bash plugins/ship/scripts/ship.sh $ARGUMENTS
```

The script will:
1. Verify the current directory is a git repo.
2. Exit early if the working tree is clean.
3. `git add -A` to stage all changes.
4. Commit with the provided message (or a default timestamped message).
5. Push to the remote (sets upstream if needed).
6. Print the result.

Report the script output to the user.

## Rules

- NEVER force push.
- NEVER skip pre-commit hooks (no `--no-verify`).
- If the commit or push fails, report the error clearly — do not retry blindly.
- If a pre-commit hook fails, fix the issue, re-stage, and create a NEW commit (never amend).
