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

1. Run `git status` to see what has changed.
2. If there are no changes (no untracked, modified, or staged files), tell the user there is nothing to ship and stop.
3. Run `git diff` and `git diff --cached` to understand the changes.
4. Run `git log --oneline -5` to see recent commit style.
5. Stage all relevant changes with `git add` (prefer adding specific files by name — avoid `-A` or `.` to prevent accidentally staging secrets or large binaries). Never stage files that look like secrets (`.env`, credentials, tokens).
6. Create a commit:
   - If the user provided a message via `$ARGUMENTS`, use that as the commit message.
   - Otherwise, write a concise commit message that summarizes the changes.
   - Always append the co-author trailer:
     ```
     Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
     ```
   - Use a HEREDOC to pass the message to `git commit -m`.
7. Push to the current branch's remote tracking branch with `git push`. If no upstream is set, use `git push -u origin HEAD`.
8. Report the result to the user: commit hash, branch, and remote URL.

## Rules

- NEVER force push.
- NEVER skip pre-commit hooks (no `--no-verify`).
- If the commit or push fails, report the error clearly — do not retry blindly.
- If a pre-commit hook fails, fix the issue, re-stage, and create a NEW commit (never amend).
