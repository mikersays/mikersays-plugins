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
2. **Not detached HEAD** — Run `git branch --show-current`. If the output is empty, the repo is in detached HEAD state. Tell the user to check out or create a branch first.
3. **Not a shallow clone** — Run `git rev-parse --is-shallow-repository`. If `true`, tell the user to run `git fetch --unshallow` first, because diffs against the base branch may be incorrect.
4. **`gh` installed** — Confirm `gh` is on the PATH (`command -v gh`). If not, tell the user to install it from https://cli.github.com/.
5. **`gh` authenticated** — Run `gh auth status`. If not authenticated, tell the user to run `gh auth login`.
6. **Remote exists** — Confirm at least one remote is configured (`git remote -v`). If there are multiple remotes, identify which one to push to: use the upstream of the current branch if set, otherwise default to `origin`.
7. **Detect base branch** — Determine the repository's default branch using this cascade:
   1. `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'` (most reliable).
   2. `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||'` (works offline if previously fetched).
   3. Fall back: check if `main` exists on the remote (`git ls-remote --heads origin main`), then `master`. If neither exists, ask the user which branch to target.
8. **Not on base branch** — If the current branch IS the base branch, tell the user to create a feature branch first.
9. **Commits ahead of base** — Run `git log --oneline <base>..HEAD`. If there are zero commits, tell the user there is nothing to open a PR for and stop.
10. **No existing PR** — Run `gh pr view --json url` (do NOT redirect stderr). Check the result:
    - If it succeeds and returns a URL, an open PR already exists — show the URL and stop.
    - If it fails with a message containing "no pull requests found", that is expected — continue.
    - If it fails for any other reason (auth error, network error, repo not found), show the error and stop.

### 2. Analyze Changes

1. Run `git diff <base>...HEAD --stat` for a file-level summary.
2. Count the diff size: `git diff <base>...HEAD | wc -l`.
   - If the diff is **under 1500 lines**, run `git diff <base>...HEAD` to get the full diff for analysis.
   - If the diff is **1500 lines or more**, skip the full diff. Use only the `--stat` output and the commit log for analysis. Note in the PR body that the diff was too large to fully analyze.
3. Note any binary files shown in `--stat` (they appear as `Bin 0 -> N bytes`). Do not attempt to diff binary content — just list the binary files in your analysis.

### 3. Push Unpushed Commits

1. Check if the current branch has an upstream: `git rev-parse --abbrev-ref @{upstream} 2>/dev/null`.
2. If no upstream, run `git push -u origin HEAD`.
3. If upstream exists, check whether local and remote have diverged:
   - Run `git rev-list --left-right --count HEAD...@{upstream}` to get `<ahead> <behind>` counts.
   - If ahead > 0 and behind == 0, run `git push`.
   - If behind > 0 (remote has commits that local does not), tell the user the branch has diverged from its upstream and they should pull or rebase first. Do NOT push.
4. **NEVER force push.**

### 4. Generate PR Content

Based on the diff analysis, generate:

- **Title**: Under 70 characters. If the user provided text via `$ARGUMENTS`, use that as the title. Otherwise, generate a concise title from the changes.
- **Summary**: 1-3 bullet points describing what changed and why.
- **Test plan**: 2-5 checkbox items (`- [ ]`) describing how to verify the changes. Be specific — reference actual files, endpoints, or behaviors.

### 5. Create the PR

Use `gh pr create` with `--base` set explicitly and a HEREDOC for the body. Use single quotes around the title to avoid shell interpretation of special characters:

```bash
gh pr create --base "$BASE_BRANCH" --title "$PR_TITLE" --body "$(cat <<'EOF'
## Summary
- First change description
- Second change description

## Test plan
- [ ] Verify first thing
- [ ] Verify second thing
- [ ] Check for regressions in related area

---
Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Important: if the title contains double quotes or shell metacharacters, escape them properly or assign to a variable first. The HEREDOC body uses `'EOF'` (single-quoted delimiter) so no expansion occurs inside the body.

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
- If `gh pr create` fails, show the full error output. Common issues:
  - Not authenticated: tell user to run `gh auth login`
  - No commits ahead of base: tell user there is nothing to PR
  - Branch not pushed: this should have been handled in step 3
  - Title too long or invalid: shorten and retry
- If the diff is empty (no changes vs base), tell the user and stop.
- Keep the PR body clean. Do not include raw diff output in the body.
- The test plan should be actionable — avoid generic items like "test everything works".
- If the repo has multiple remotes (common in fork workflows), prefer pushing to the remote that the current branch already tracks. If no tracking is set, use `origin`. Tell the user which remote was used.
