# mikersays-plugins

A marketplace of plugins for Claude Code and Codex CLI.

## Install — Claude Code

```bash
/plugin marketplace add mikersays/mikersays-plugins
```

Then install any plugin:

```bash
/plugin install pr@mikersays-plugins
```

## Install — Codex CLI

**Native (recommended):**

```bash
codex plugin marketplace add mikersays/mikersays-plugins
codex plugin add pr@mikersays-plugins
```

Repeat `codex plugin add <plugin>@mikersays-plugins` for each plugin you want.

**Headless (one-liner):**

```bash
codex exec --full-auto --add-dir ~/.codex --skip-git-repo-check \
  "Run: codex plugin marketplace add mikersays/mikersays-plugins && codex plugin add pr@mikersays-plugins. Verify the plugin install and report the result."
```

**Interactive** — paste this prompt into a Codex session:

```
Read https://raw.githubusercontent.com/mikersays/mikersays-plugins/master/INSTALL.md and use Codex's native plugin commands to add the mikersays/mikersays-plugins marketplace. Then install the requested plugins with codex plugin add <plugin>@mikersays-plugins and report the final result.
```

Codex records the marketplace and installed plugins in `~/.codex/config.toml`, then manages plugin snapshots and cache files under `~/.codex`.

## Plugins

| Plugin | Description | Usage |
|--------|-------------|-------|
| [tech-writer](plugins/tech-writer/) | Review and rewrite docs using Google's Technical Writing guidelines or Simplified Technical English | `/tech-writer [file path] [ste\|google]` |
| [diagram](plugins/diagram/) | Generate interactive SVG diagrams from a description | `/diagram [description]` |
| [bootcamp](plugins/bootcamp/) | Swarm of expert subagents builds an interactive zero-to-hero course site — modules, worked examples, exercises with solutions, checkpoints, a capstone, and progress tracking — shipped to `docs/` and deployed on GitHub Pages | `/bootcamp [topic]` |
| [pr](plugins/pr/) | Create a GitHub PR with auto-generated title, summary, and test plan | `/pr [title]` |
| [handoff](plugins/handoff/) | Audit session context and persist what matters for the next agent | `/handoff` |
| [slop](plugins/slop/) | Rewrite any text to maximally overuse every known AI-writing tell | `/slop [file \| text \| topic]` |
| [gh-pages](plugins/gh-pages/) | Build or publish a static site on GitHub Pages — saves the site to `docs/` and enables Pages from the `docs/` folder on the default branch | `/gh-pages [site description]` |
| [okf](plugins/okf/) | Author, index, and validate Open Knowledge Format (OKF v0.2) knowledge bundles — markdown concepts with frontmatter for provenance, trust, lifecycle, and attested computations | `/okf-init` `/okf-new` `/okf-index` `/okf-validate` |
| [expert](plugins/expert/) | Rewrite a task prompt the way a top professional would approach it: expert habits, raw sources, named methods, and independent proof | `/expert [task]` |
| [maintenance](plugins/maintenance/) | Sync docs, run installer, run uninstaller | `/sync-docs` `/install-marketplace` `/uninstall-marketplace` |

## Contributing

1. Create a directory under `plugins/<name>/`
2. Add `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` (name, description, version; codex also needs `"skills": "./skills/"` and an `interface` object)
3. Add your skills under `skills/<skill-name>/SKILL.md` (optionally add `agents/openai.yaml` for Codex UI metadata)
4. Add a `README.md` for documentation
5. Run `/sync-docs` (from the `maintenance` plugin) to register the plugin across all three marketplace files, `INSTALL.md`, `UNINSTALL.md`, and `docs/index.html`
6. Run `python3 scripts/validate.py` to confirm consistency. Enable the pre-commit hook once per clone with `git config core.hooksPath .githooks` so this runs automatically.
