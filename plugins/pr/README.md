# pr

Create a GitHub pull request with an auto-generated title, summary, and test plan.

## Install

```bash
/plugin install pr@mikersays-plugins
```

## Usage

```bash
/pr
/pr Add user authentication module
```

If you provide a message, it becomes the PR title. Otherwise the title is generated from the commit history.

## What it does

1. Runs preflight checks (git repo, `gh` CLI, authentication, remote, branch)
2. Analyzes the diff between your branch and the base branch
3. Auto-pushes unpushed commits (never force pushes)
4. Creates a PR with:
   - A concise title (under 70 characters)
   - A summary section with 1-3 bullet points
   - A test plan with checkbox items for GitHub UI interactivity
5. Returns the PR URL

## Safety

- Never force pushes
- Never creates commits or modifies git config
- Checks for existing open PRs before creating a new one
- Requires `gh` CLI to be installed and authenticated

## Requirements

- [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated
- A git repository with a remote
- A branch that is not the base branch (main/master)
