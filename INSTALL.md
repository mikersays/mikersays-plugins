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

> **Important:** These steps write to `~/.codex` and `~/.agents`. The headless command uses `--add-dir` to grant the agent write access to exactly those two directories — no broader sandbox escalation required.

### Step 1: Clone or update the repo

Check whether `~/.codex/plugins/mikersays/mikersays-plugins` exists.

**If it does not exist:**
```bash
mkdir -p ~/.codex/plugins/mikersays
git clone https://github.com/mikersays/mikersays-plugins.git ~/.codex/plugins/mikersays/mikersays-plugins
```

**If it already exists:**
- Run `git -C ~/.codex/plugins/mikersays/mikersays-plugins pull --ff-only` to update.
- If already up to date, report that and continue.

### Step 2: Create or update marketplace.json

Target file: `~/.agents/plugins/marketplace.json`

Read the file if it exists and inspect its root structure, then follow the matching case:

**Case A — file does not exist:**
Create `~/.agents/plugins/` if needed, then write the file as a JSON array containing only the mikersays entry:
```json
[
  <mikersays-entry>
]
```

**Case B — file exists and root is a JSON array (`[...]`):**
Remove any existing element whose `"id"` is `"mikersays-marketplace"`, then append the mikersays entry to the array.

**Case C — file exists and root is a JSON object (`{...}`):**
This is a single-marketplace file. Wrap the existing object and the mikersays entry together into an array:
```json
[
  <existing-object>,
  <mikersays-entry>
]
```

In all cases, the mikersays entry to insert is:

```json
{
  "name": "mikersays-marketplace",
  "interface": {
    "displayName": "mikersays Plugins"
  },
  "plugins": [
    {
      "name": "ship",
      "source": { "path": "../../.codex/plugins/mikersays/mikersays-plugins/plugins/ship" }
    },
    {
      "name": "pr",
      "source": { "path": "../../.codex/plugins/mikersays/mikersays-plugins/plugins/pr" }
    },
    {
      "name": "tech-writer",
      "source": { "path": "../../.codex/plugins/mikersays/mikersays-plugins/plugins/tech-writer" }
    },
    {
      "name": "deck",
      "source": { "path": "../../.codex/plugins/mikersays/mikersays-plugins/plugins/deck" }
    },
    {
      "name": "roadmap",
      "source": { "path": "../../.codex/plugins/mikersays/mikersays-plugins/plugins/roadmap" }
    },
    {
      "name": "diagram",
      "source": { "path": "../../.codex/plugins/mikersays/mikersays-plugins/plugins/diagram" }
    }
  ]
}
```

### Step 3: Install the startup hook

Target file: `~/.codex/hooks.json`

- If it does not exist, create it containing only the structure below.
- If it already exists, merge: preserve all existing hook entries and append the new handler to the `SessionStart` array (create the array key if absent).

```json
{
  "hooks": {
    "SessionStart": [
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
    ]
  }
}
```

### Step 3b: Enable plugins in config.toml

Open `~/.codex/config.toml` and append the following entries (skip any that already exist):

```toml
[plugins."ship@mikersays-marketplace"]
enabled = true

[plugins."pr@mikersays-marketplace"]
enabled = true

[plugins."tech-writer@mikersays-marketplace"]
enabled = true

[plugins."deck@mikersays-marketplace"]
enabled = true

[plugins."roadmap@mikersays-marketplace"]
enabled = true

[plugins."diagram@mikersays-marketplace"]
enabled = true
```

### Step 4: Verify

Run the following checks and report the result for each:

1. `ls ~/.codex/plugins/mikersays/mikersays-plugins/.codex-plugin/marketplace.json` — confirm repo is present
2. `cat ~/.agents/plugins/marketplace.json` — confirm marketplace entry exists
3. `cat ~/.codex/hooks.json` — confirm SessionStart hook is present
4. `git -C ~/.codex/plugins/mikersays/mikersays-plugins log --oneline -1` — show the installed commit
