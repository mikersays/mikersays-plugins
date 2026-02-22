# ship

Git commit and push in one command.

## Usage

```
/ship                     # auto-generates a commit message
/ship fix login redirect  # uses your message
```

## Installation

Copy the `ship` directory into your Claude Code skills folder:

```bash
# Global (all projects)
cp -r ship ~/.claude/skills/

# Project-level
cp -r ship .claude/skills/
```

## What it does

1. Checks for changes
2. Stages files (skipping secrets/binaries)
3. Commits with a message (yours or auto-generated)
4. Pushes to the remote
