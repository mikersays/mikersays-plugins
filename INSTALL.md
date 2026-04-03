# mikersays-plugins — Codex Installer

This page installs the mikersays plugin marketplace for Codex on the current machine.

## What this sets up

Clones or updates the marketplace repo to:
`~/.codex/plugins/mikersays/mikersays-plugins`

Creates or updates the personal Codex marketplace file at:
`~/.agents/plugins/marketplace.json`

Installs a `SessionStart` hook at:
`~/.codex/hooks.json`

The hook runs `git pull` on the marketplace repo each time Codex starts, so plugins stay current automatically.

## Available plugins

- `ship` — Git commit and push in one command
- `pr` — Create a GitHub PR with auto-generated title, summary, and test plan
- `tech-writer` — Review and rewrite docs using Google's Technical Writing guidelines
- `deck` — Generate a self-contained HTML slide deck from a topic
- `roadmap` — Generate a visual HTML Gantt-chart roadmap from a markdown file
- `diagram` — Generate interactive SVG diagrams from a description

## Prompt to give Codex

```
Read @INSTALL.md and follow the instructions exactly to install the mikersays-plugins marketplace on this machine. Create or update the local marketplace file and hooks config, verify the install, and tell me the final result.
```

---

## Instructions for Codex

### Step 1: Clone or update the repo

Check whether `~/.codex/plugins/mikersays/mikersays-plugins` exists.

**If it does not exist:**
```bash
mkdir -p ~/.codex/plugins/mikersays
git clone https://github.com/mikersays/mikersays-plugins.git ~/.codex/plugins/mikersays/mikersays-plugins
```

**If it already exists:**
- Read `.codex-plugin/marketplace.json` inside it to get the current state.
- Run `git -C ~/.codex/plugins/mikersays/mikersays-plugins pull --ff-only` to update.
- If already up to date, report that and continue.

### Step 2: Create or update marketplace.json

Ensure this file exists: `~/.agents/plugins/marketplace.json`

- If it does not exist, create it with an empty `[]` top-level array, then add the entry below.
- If it already exists, preserve any unrelated marketplace entries and add or replace the entry whose `id` is `"mikersays-marketplace"`.

Use this marketplace entry:

```json
{
  "id": "mikersays-marketplace",
  "interface": {
    "displayName": "mikersays Plugins"
  },
  "plugins": [
    {
      "id": "ship",
      "interface": { "displayName": "ship" },
      "source": { "path": "../../.codex/plugins/mikersays/mikersays-plugins/plugins/ship" }
    },
    {
      "id": "pr",
      "interface": { "displayName": "pr" },
      "source": { "path": "../../.codex/plugins/mikersays/mikersays-plugins/plugins/pr" }
    },
    {
      "id": "tech-writer",
      "interface": { "displayName": "tech-writer" },
      "source": { "path": "../../.codex/plugins/mikersays/mikersays-plugins/plugins/tech-writer" }
    },
    {
      "id": "deck",
      "interface": { "displayName": "deck" },
      "source": { "path": "../../.codex/plugins/mikersays/mikersays-plugins/plugins/deck" }
    },
    {
      "id": "roadmap",
      "interface": { "displayName": "roadmap" },
      "source": { "path": "../../.codex/plugins/mikersays/mikersays-plugins/plugins/roadmap" }
    },
    {
      "id": "diagram",
      "interface": { "displayName": "diagram" },
      "source": { "path": "../../.codex/plugins/mikersays/mikersays-plugins/plugins/diagram" }
    }
  ]
}
```

### Step 3: Install the startup hook

Ensure this file exists: `~/.codex/hooks.json`

- If it does not exist, create it with `{ "hooks": {} }`.
- If it already exists, preserve existing hook entries and merge in the new handler below.

Add this handler to the `SessionStart` array (create the array if absent):

```json
{
  "matcher": ".*",
  "hooks": [
    {
      "type": "command",
      "command": "git -C ~/.codex/plugins/mikersays/mikersays-plugins pull --ff-only --quiet 2>&1 | grep -v 'Already up to date' || true",
      "statusMessage": "Updating mikersays-plugins...",
      "timeout": 30
    }
  ]
}
```

### Step 4: Verify

Run the following checks and report the result for each:

1. `ls ~/.codex/plugins/mikersays/mikersays-plugins/.codex-plugin/marketplace.json` — confirm repo is present
2. `cat ~/.agents/plugins/marketplace.json` — confirm marketplace entry exists
3. `cat ~/.codex/hooks.json` — confirm SessionStart hook is present
4. `git -C ~/.codex/plugins/mikersays/mikersays-plugins log --oneline -1` — show the installed commit
