# mikersays-plugins — Codex Native Install

This page installs the mikersays plugin marketplace with Codex's native plugin commands.

## What this sets up

Adds the GitHub marketplace:

```bash
codex plugin marketplace add mikersays/mikersays-plugins
```

Then installs plugins from that marketplace using:

```bash
codex plugin add <plugin>@mikersays-plugins
```

## Available plugins

- `pr` — Create a GitHub PR for the current branch with auto-generated title, summary, and test plan
- `tech-writer` — Review and rewrite documentation in place using either Google's Technical Writing guidelines or strict Simplified Technical English (ASD-STE100), chosen per document — Google for READMEs, guides, and ordinary prose; STE for procedures, runbooks, and docs headed for translation
- `diagram` — Generate an interactive SVG diagram (architecture, sequence, flowchart, ER) from a description
- `bootcamp` — Spin up a swarm of expert subagents to build an interactive zero-to-hero course site on any topic — progressive modules, worked examples, exercises with solutions, checkpoints, a capstone, and progress tracking — shipped to docs/ and deployed on GitHub Pages
- `plan` — Lightweight markdown-based tracker for bugs/features/chores/todos that lives in docs/plan/ inside your repo; includes `plan-init`, `plan-add`, `plan-list`, `plan-update`, and `plan-close`
- `handoff` — Audit session context and persist what matters for the next agent — decisions, dead ends, insights, and in-flight work
- `slop` — Rewrite any text to maximally overuse every known AI-writing tell — em-dashes, the rule of three, "not X but Y", and the rest
- `gh-pages` — Build or publish a static site on GitHub Pages — saves the site to docs/ and enables Pages from the docs/ folder on the default branch
- `okf` — Author, index, and validate Open Knowledge Format (OKF v0.2) bundles — markdown concepts with YAML frontmatter for provenance, trust, lifecycle, and attested computations; includes `okf-init`, `okf-new`, `okf-index`, and `okf-validate`
- `expert` — Turn a task description into a deeper, expert-grade prompt — what a top professional would do, their raw sources, methods and tools, and independent proof the result is right

## Install

First add the marketplace:

```bash
codex plugin marketplace add mikersays/mikersays-plugins
```

Then install one or more plugins:

```bash
codex plugin add pr@mikersays-plugins
codex plugin add pr@mikersays-plugins
codex plugin add tech-writer@mikersays-plugins
```

Repeat `codex plugin add <plugin>@mikersays-plugins` for any plugin listed above.

## Prompt to give Codex

```
Read @INSTALL.md and use Codex's native plugin commands to add the mikersays/mikersays-plugins marketplace. Then install the requested plugins with codex plugin add <plugin>@mikersays-plugins and report the final result.
```
