---
name: pr
description: Create a GitHub PR for the current branch with auto-generated title, summary, and test plan
argument-hint: "[PR title]"
allowed-tools: Bash
---

# PR — Create a GitHub Pull Request

Analyze the current branch and open a pull request via `gh pr create`. The user invokes this when their work is ready for review.

## 1. Preflight

Run these checks. If any fail, tell the user the specific fix and stop.

1. Inside a git repo: `git rev-parse --is-inside-work-tree`.
2. Branch is checked out (not detached HEAD): `git branch --show-current` returns non-empty.
3. Not a shallow clone: `git rev-parse --is-shallow-repository` returns `false`. Shallow clones produce wrong base diffs — ask the user to run `git fetch --unshallow`.
4. `gh` is installed (`command -v gh`) and authenticated (`gh auth status`).
5. At least one remote exists (`git remote -v`).
6. Detect the base branch in this order:
   - `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'` (most reliable)
   - `git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's|refs/remotes/origin/||'` (offline fallback)
   - Probe `main` then `master` via `git ls-remote --heads origin <name>`. If neither, ask the user.
7. Current branch is not the base branch.
8. There are commits ahead of base: `git log --oneline <base>..HEAD` is non-empty.
9. No open PR already exists for this branch. Run `gh pr view --json url` (do not redirect stderr — you need to read the error).
   - Success with a URL → an open PR exists; show the URL and stop.
   - Error containing "no pull requests found" → expected, continue.
   - Any other error (auth, network, missing repo) → show it and stop.

## 2. Analyze the diff

Get a file-level summary with `git diff <base>...HEAD --stat`, then size the diff with `git diff <base>...HEAD | wc -l`:

- Under 1500 lines: read the full diff.
- 1500+ lines: skip the full diff, work from `--stat` plus `git log <base>..HEAD`, and note in the PR body that the diff was too large to fully analyze.

List binary files (shown as `Bin 0 -> N bytes`) by name only — don't try to diff their contents.

## 3. Push unpushed commits

Check the upstream with `git rev-parse --abbrev-ref @{upstream} 2>/dev/null`:

- No upstream → `git push -u origin HEAD` (or the tracked remote if the branch already tracks one; in fork workflows tell the user which remote you used).
- Upstream exists → check divergence with `git rev-list --left-right --count HEAD...@{upstream}` (gives `<ahead> <behind>`). If only ahead, `git push`. If behind, the branch has diverged — stop and ask the user to pull or rebase first.

Never force push, and never create or amend commits. The skill ships existing history; it doesn't rewrite it.

## 4. Generate PR content

- **Title** — under 70 characters. If the user passed text via `$ARGUMENTS`, use it verbatim. Otherwise generate a concise title from the diff and commit messages.
- **Summary** — 1–3 bullets covering what changed and why.
- **Test plan** — 2–5 checkbox items (`- [ ]`). Reference real files, endpoints, or behaviors so a reviewer knows exactly what to verify. Skip generic items like "test that it works".

## 5. Create the PR

Pass the title via a variable and the body via a single-quoted heredoc — that way titles with quotes/backticks and bodies with `$` or backticks survive shell expansion intact.

Input — branch with two commits adding a `/healthz` endpoint and its test:

```bash
PR_TITLE="Add /healthz endpoint for liveness checks"
gh pr create --base "$BASE_BRANCH" --title "$PR_TITLE" --body "$(cat <<'EOF'
## Summary
- Add `GET /healthz` returning `{"status":"ok"}` for load balancer probes
- Wire the route into `server/router.ts` and cover it in `server/healthz.test.ts`

## Test plan
- [ ] `curl localhost:3000/healthz` returns 200 with `{"status":"ok"}`
- [ ] `npm test -- healthz` passes
- [ ] Existing routes in `server/router.ts` still resolve

---
Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Pass `--base` explicitly so the PR targets the branch you detected, not whatever GitHub guesses.

If `gh pr create` fails, show the full error. Most failures map to a preflight check that should have caught the issue (auth, no commits, unpushed branch); a title that's too long or contains invalid characters is the main runtime case — shorten and retry.

## 6. Report

Print the PR URL returned by `gh pr create`, the title, the base branch, and the number of commits included.
