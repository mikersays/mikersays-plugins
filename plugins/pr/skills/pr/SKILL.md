---
name: pr
description: Create a GitHub PR with auto-generated title, summary, and test plan
argument-hint: "[PR title]"
allowed-tools: Bash
---

# PR — Create a GitHub Pull Request

Analyze the current branch's changes and create a GitHub pull request with a generated title, summary, and test plan.

## Process

### 1. Preflight Checks

Run these checks in order. If any fail, stop and tell the user what to fix.

1. **Git repo** — Confirm this is a git repository (`git rev-parse --is-inside-work-tree`).
2. **`gh` installed** — Confirm `gh` is on the PATH (`command -v gh`). If not, tell the user to install it from https://cli.github.com/.
3. **`gh` authenticated** — Run `gh auth status`. If not authenticated, tell the user to run `gh auth login`.
4. **Remote exists** — Confirm at least one remote is configured (`git remote -v`).
5. **Not on base branch** — Detect the base branch (`main` or `master`, whichever exists on the remote). If the current branch IS the base branch, tell the user to create a feature branch first.
6. **No existing PR** — Run `gh pr view --json url 2>/dev/null`. If an open PR already exists for this branch, show its URL and stop.

### 2. Analyze Changes

1. Determine the base branch (try `main`, fall back to `master`).
2. Run `git log --oneline <base>..HEAD` to get the commit list.
3. Run `git diff <base>...HEAD --stat` for a file-level summary.
4. Run `git diff <base>...HEAD` for the full diff (if very large, use `--stat` only and note that the diff was too large to fully analyze).

### 3. Push Unpushed Commits

1. Check if the current branch has an upstream: `git rev-parse --abbrev-ref @{upstream} 2>/dev/null`.
2. If no upstream, run `git push -u origin HEAD`.
3. If upstream exists, compare `git rev-parse HEAD` with `git rev-parse @{upstream}`. If they differ, run `git push`.
4. **NEVER force push.**

### 4. Generate PR Content

Based on the diff analysis, generate:

- **Title**: Under 70 characters. If the user provided text via `$ARGUMENTS`, use that as the title. Otherwise, generate a concise title from the changes.
- **Summary**: 1–3 bullet points describing what changed and why.
- **Test plan**: 2–5 checkbox items (`- [ ]`) describing how to verify the changes. Be specific — reference actual files, endpoints, or behaviors.

### 5. Create the PR

Use `gh pr create` with a HEREDOC for the body:

```bash
gh pr create --title "THE TITLE" --body "$(cat <<'EOF'
## Summary
- First change description
- Second change description

## Test plan
- [ ] Verify first thing
- [ ] Verify second thing
- [ ] Check for regressions in related area

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### 6. Report

Tell the user:
- The PR URL (returned by `gh pr create`)
- The title and base branch
- Number of commits included

## Rules

- **NEVER force push.** Only use `git push` or `git push -u origin HEAD`.
- **NEVER create commits.** This skill only creates PRs from existing commits.
- **NEVER modify git config.** Do not change user.name, user.email, or any other git config.
- **NEVER amend commits.** Leave the commit history as-is.
- If `gh pr create` fails, show the error. Common issues:
  - Not authenticated → tell user to run `gh auth login`
  - No commits ahead of base → tell user there's nothing to PR
  - Branch not pushed → this should have been handled in step 3
- If the diff is empty (no changes vs base), tell the user and stop.
- Keep the PR body clean. Do not include raw diff output in the body.
- The test plan should be actionable — avoid generic items like "test everything works".
