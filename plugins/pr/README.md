# pr

Create a GitHub pull request with an auto-generated title, summary, and test plan.

## Usage

```
/pr
/pr Add user authentication module
```

If you provide a title, the skill uses that text as the PR title. Otherwise, the skill generates a title from the commit history.

## Installation

```bash
/plugin install pr@mikersays-plugins
```

## Requirements

Before using `/pr`, confirm you have the following:

- [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated (`gh auth login`)
- A git repository with at least one remote configured
- A feature branch checked out — not `main` or `master`

## What it does

1. Runs preflight checks: git repo, `gh` CLI, authentication, remote, and branch
2. Analyzes the diff between your branch and the base branch
3. Pushes any unpushed commits (never force-pushes)
4. Creates a PR with:
   - A concise title (under 70 characters)
   - A summary with 1–3 bullet points describing what changed
   - A test plan with checkbox items for easy review in the GitHub UI
5. Prints the new PR URL

## Safety

The skill never:

- Force-pushes
- Creates commits or amends existing ones
- Modifies git config

The skill also checks for an existing open PR on your branch before creating a new one, and stops if one already exists.
