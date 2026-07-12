# gh-pages

Build or publish a static site on GitHub Pages the right way: every site file goes in `docs/` on the default branch, and when the site is ready the skill enables Pages from the `docs/` folder via the GitHub API and hands you the live URL.

## Usage

```
/gh-pages a landing page for my CLI tool   # build a new site into docs/ and deploy it
/gh-pages ./site                           # move existing site files into docs/ and deploy
```

The skill also triggers implicitly — "make me a GitHub Pages site for X" or "publish this on GitHub Pages" is enough.

## What it does

1. Writes (or moves) the site into `docs/` — `docs/index.html` entry point, relative asset URLs, `.nojekyll`
2. Commits only the site files and pushes (asks before creating a new GitHub repo; never changes visibility)
3. Enables Pages from the `docs/` folder on the default branch via `gh api` (POST, or PUT if already configured)
4. Polls the build, verifies the URL responds, and reports the live link
5. Sets the repo's About **Website** field to the Pages URL (the API equivalent of the "Use your GitHub Pages website" toggle) so the site is one click away from the repo page

## Requirements

- `gh` CLI, authenticated (`gh auth login`)
- A GitHub repository (the skill offers `git init` / `gh repo create` if missing)
