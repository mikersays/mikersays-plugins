# maintenance

Maintainer-only skills for the mikersays-plugins marketplace itself. Not installed by end users — the registries mark it `NOT_AVAILABLE` and it is deliberately absent from `INSTALL.md`, `UNINSTALL.md`, and the landing page.

| Command | What it does |
|---|---|
| `/sync-docs` | Propagate `plugins/` changes into the three marketplace JSON files, `README.md`, `INSTALL.md`, `UNINSTALL.md`, and `docs/index.html`. |
| `/install-marketplace` | Self-installer a Codex agent runs to set the marketplace up on a machine — clone, skill symlinks, registry entry, SessionStart hook. |
| `/uninstall-marketplace` | Reverses the installer: removes everything it placed without touching other marketplaces or config. |

After any marketplace change, run `python3 scripts/validate.py` (also enforced by the pre-commit hook and CI) to confirm everything stayed consistent.
