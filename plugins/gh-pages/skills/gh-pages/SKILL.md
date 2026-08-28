---
name: gh-pages
description: Build or publish a static site on GitHub Pages — save all site files to docs/, then enable Pages serving from the docs/ folder on the default branch and report the live URL. Use whenever the user asks to make, create, deploy, publish, or host a GitHub Pages site.
argument-hint: "[what the site is about, or path to existing site files]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
---

# GitHub Pages — build into `docs/`, deploy from the default branch

This skill governs **any** request to create or publish a GitHub Pages site. It has two non-negotiable outcomes:

1. **Every site file lives in `docs/` at the repo root.** Never `gh-pages` branch, never repo root, never a custom folder.
2. **On completion, Pages is actually enabled** via the GitHub API so the user gets a live URL — not instructions to click through Settings themselves.

## Step 1 — Establish the site content in `docs/`

- **Building a new site:** write it directly into `docs/` — `docs/index.html` as the entry point, assets under `docs/assets/` (css/js/images). Self-contained static HTML/CSS/JS with no build step.
- **Site files already exist elsewhere** (e.g. `site/`, `public/`, repo root): move them into `docs/` with `git mv` (or plain `mv` if untracked), preserving structure so `docs/index.html` exists.
- **Repo already has an unrelated `docs/`** (e.g. plain markdown docs): stop and ask the user before overwriting or mixing — never clobber existing content silently.

Rules for the files themselves:

- **Relative URLs only.** A project site is served at `https://<owner>.github.io/<repo>/`, not at the domain root — root-absolute paths like `/assets/main.css` 404. Use `assets/main.css` or `./assets/main.css`.
- **Add `docs/.nojekyll`** (empty file) so GitHub serves files and directories starting with `_` and skips the Jekyll build entirely for plain HTML sites.
- No placeholders: no "TODO", no lorem ipsum, no broken links between pages.
- Sanity-check locally before deploying when the site has any interactivity: `cd docs && python3 -m http.server 4173` and curl or open the pages; kill the server afterward. Include a narrow-viewport pass in this check (see below) — desktop-only testing is what let this bug ship repeatedly in the past.

### Mobile responsiveness (required, not optional)

A prior audit across every site this skill had built found a viewport tag alone is not sufficient: the recurring, user-visible failure is code blocks and other wide content that force horizontal pinch-zoom-and-pan on a phone. Every site built with this skill must satisfy all of the following:

- **Viewport meta tag**, always, in every HTML page's `<head>`:
  ```html
  <meta name="viewport" content="width=device-width, initial-scale=1">
  ```
- **No fixed-width root containers.** The page's outermost wrapper/shell/container element must use `max-width` (with `width: 100%` or no `width` set) plus `margin-inline: auto`, never a bare `width: <N>px` that doesn't shrink below `N`. Fluid units (`%`, `rem`, `clamp()`, `minmax(0, 1fr)`) over fixed px for anything that spans the page.
- **`<pre>`/code blocks must wrap on narrow screens, not only scroll.** `overflow-x: auto` alone is not enough — on a touchscreen there is no visible affordance that the box scrolls independently of the page, so users pinch-zoom-out and pan the whole page instead, which doesn't work. Always pair it with a mobile breakpoint that wraps:
  ```css
  pre {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
  @media (max-width: 640px) {
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      overflow-wrap: anywhere;
    }
  }
  ```
- **Tables** with more than 2-3 columns of prose-length content: wrap in a container with `overflow-x: auto` at minimum; prefer a layout that reflows to stacked rows below ~600px if the table is central to the page.
- **Images/media**: always `max-width: 100%; height: auto;` — never a bare fixed pixel width on an `<img>` or `<video>`.
- Before declaring the site done, mentally (or via the local server plus a resized/narrow browser window) walk through every page — not just the homepage — at a ~390px-wide viewport and confirm no element requires horizontal scrolling of the page itself, and that any code samples are either short enough to fit or wrap.

### Canvas UI design pass (new sites and substantial redesigns)

During visual planning, browse [Canvas UI](https://canvasui.dev/) and its [component gallery](https://canvasui.dev/components), then consider whether one of its creative canvas/WebGL effects would strengthen the site's concept. This is a required consideration, not a requirement to force an effect into every site. Use at most one prominent effect, and only when it adds meaning or atmosphere without competing with the content.

- These are no-build static sites. Prefer Canvas UI's vanilla variant, keep the source local under `docs/assets/`, and commit browser-ready JavaScript. If the source needs TypeScript or bundling, perform that work during authoring; the deployed site must not require npm, a CDN, or a runtime build step.
- Preserve Canvas UI's copyright and permission notice in the copied source or a `docs/THIRD_PARTY_NOTICES.md` file. Do not redistribute the component as a standalone library.
- Provide a clean non-WebGL fallback, honor `prefers-reduced-motion`, keep page content usable with JavaScript disabled, and test pointer, keyboard, touch, mobile layout, and performance before shipping.
- If no component is a strong fit, continue with purpose-built HTML/CSS/JS rather than adding spectacle for its own sake.

## Step 2 — Commit and push

1. If not inside a git repo: `git init`, then continue (the remote question comes next).
2. Stage **only** the site files (`git add docs/`) — never `git add -A` in a repo with unrelated changes. Commit with a message describing the site. End the commit message with the standard Co-Authored-By trailer if this session uses one.
3. **Remote handling:**
   - **Remote exists:** `git push` (with `-u origin <branch>` if no upstream). Preserve the repository's current visibility — if it is private, keep it private, never offer to make it public, and assume private-repo Pages is available unless the API rejects it.
   - **No remote:** creating a GitHub repository is a new outward-facing resource — **ask the user before creating it**, proposing `gh repo create <name> --public --source=. --remote=origin --push` as the default.
4. Resolve facts from the repo rather than assuming:
   ```bash
   BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@.*/@@')
   [ -z "$BRANCH" ] && BRANCH=$(git branch --show-current)
   REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
   ```
   The default branch may be `master`, not `main` — always use the resolved `$BRANCH`.

## Step 3 — Enable Pages from `docs/` (the completion step, do not skip)

```bash
gh api -X POST "repos/$REPO/pages" \
  -f "source[branch]=$BRANCH" -f "source[path]=/docs"
```

- If Pages is **already configured** (POST returns 409), update the source instead:
  ```bash
  gh api -X PUT "repos/$REPO/pages" \
    -f "source[branch]=$BRANCH" -f "source[path]=/docs"
  ```
- If `gh` is not authenticated (`gh auth status` fails), tell the user to run `gh auth login` (suggest they type `! gh auth login` if the client supports it), then retry — do not fall back to manual Settings instructions until auth is genuinely unavailable.
- If the API rejects enablement on a private repo for plan/billing reasons, report that exact error; do not change repo visibility to work around it.

## Step 4 — Verify and report

1. Poll until the first build finishes:
   ```bash
   gh api "repos/$REPO/pages/builds/latest" --jq .status   # repeat until "built" (or "errored")
   ```
2. Get the canonical URL and check it responds:
   ```bash
   URL=$(gh api "repos/$REPO/pages" --jq .html_url)
   curl -s -o /dev/null -w "%{http_code}" "$URL"
   ```
   A fresh site can return 404 for a minute or two after the build reports `built` — retry briefly before treating it as a failure.
3. **Set the repository's Website field to the Pages site (always, not optional).** In the repo's About section this is the "Use your GitHub Pages website" toggle; that checkbox itself is not exposed via the API, so achieve the same result by writing the exact Pages URL into the homepage field:
   ```bash
   gh repo edit "$REPO" --homepage "$URL"
   ```
   Use the `html_url` captured in step 2 verbatim — do not hand-construct the URL. Never overwrite a *different* pre-existing homepage without asking.
4. Report to the user: the live URL, the HTTP status observed, and that Pages serves from `docs/` on `$BRANCH` (so future edits to `docs/` auto-deploy on push).

## What this skill must NOT do

- Put site files anywhere other than `docs/`, or deploy via a `gh-pages` branch or GitHub Actions workflow — the `/docs` folder source is the contract.
- Change repository visibility, force-push, or commit unrelated files.
- Declare success without having enabled Pages and observed the URL respond.
- Ship a page with a fixed-width root container, a `<pre>` block that only scrolls (no mobile wrap), or a bare fixed-width image — see Mobile responsiveness above.
