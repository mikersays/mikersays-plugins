---
type: Playbook
title: Validate the marketplace
description: What scripts/validate.py checks, where it runs, and how to keep the shared diagram assets identical.
tags: [validation, ci]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-10-07T07:53:13Z }
status: draft
sources:
  - id: claude-md
    resource: ../CLAUDE.md
    title: Repository agent guidance
  - id: validate
    resource: ../scripts/validate.py
    title: Marketplace validator
---

# Run it

```bash
python3 scripts/validate.py          # stdlib only, Python 3.9+
git config core.hooksPath .githooks  # once per clone, enables the pre-commit hook
```

The same check runs in `.githooks/pre-commit` and in `.github/workflows/validate.yml` on every push and PR.[^claude-md]

# What it checks

* All three marketplace JSON files parse and list every `plugins/<name>/` directory.
* `CLAUDE.md` and `AGENTS.md` both exist.
* Each plugin has both manifests, and their `name` fields match. Each Codex manifest has an `interface` object.
* Each `SKILL.md` has parseable frontmatter, and `name` matches its directory.
* Each `agents/openai.yaml` has an `interface:` key and is non-empty.
* Each bundled `plugins/**/*.py` compiles, and any script that supports `--selftest` passes it.
* Shared assets are byte-identical in every plugin that ships a copy.
* Every user-facing plugin and skill (all but `maintenance`) appears in `INSTALL.md`, `UNINSTALL.md`, and `docs/index.html`.[^claude-md][^validate]

# Shared diagram assets

`deck`, `gh-pages`, `monograph`, and `bootcamp` each ship a copy of `diagram-zoom.js`, `diagram-zoom.css`, and `references/mermaid-diagrams.md`, because plugins install independently and cannot share files. Edit one copy, then copy it to the other three. The validator fails if they diverge.[^claude-md]

[^claude-md]: CLAUDE.md
[^validate]: scripts/validate.py
