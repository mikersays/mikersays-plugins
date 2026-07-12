# ship

Git commit and push in one command.

## Usage

```
/ship                     # auto-generates a commit message
/ship fix login redirect  # uses your message
```

## Installation

Install through the marketplace so the skill and its script land together:

```bash
# Claude Code (inside the CLI)
/plugin marketplace add mikersays/mikersays-plugins
/plugin install ship@mikersays-plugins

# Codex CLI
codex plugin marketplace add mikersays/mikersays-plugins
codex plugin add ship@mikersays-plugins
```

## Standalone script

You can also run the ship script directly from any repo:

```bash
bash plugins/ship/scripts/ship.sh "your commit message"
```

## What it does

1. Checks for changes
2. Stages everything (`git add -A`)
3. Commits with a message (yours or auto-generated with timestamp)
4. Pushes to the remote (sets upstream if needed)
