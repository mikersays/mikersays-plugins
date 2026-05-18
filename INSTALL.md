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

- `ship` — Stage, commit, and push all changes in one step, with auto-generated message if none given
- `pr` — Create a GitHub PR for the current branch with auto-generated title, summary, and test plan
- `tech-writer` — Review and rewrite documentation in place using Google's Technical Writing guidelines
- `deck` — Generate a self-contained HTML slide deck from a topic — single file, dark theme, keyboard nav
- `roadmap` — Generate a self-contained interactive HTML Gantt chart from a markdown roadmap file
- `diagram` — Generate an interactive SVG diagram (architecture, sequence, flowchart, ER) from a description
- `plan` — Lightweight markdown-based tracker for bugs/features/chores/todos that lives in docs/plan/ inside your repo

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
    },
    {
      "name": "plan",
      "source": { "path": "../../.codex/plugins/mikersays/mikersays-plugins/plugins/plan" }
    }
  ]
}
```

### Step 3: Symlink skills into ~/.agents/skills

Codex's `/skills` command scans `~/.agents/skills/`. Create symlinks there so all skills appear.

`ship`, `pr`, `tech-writer`, `deck`, `roadmap`, and `diagram` each ship a single same-named skill — one symlink per plugin. The `plan` plugin ships five skills (`plan-init`, `plan-add`, `plan-list`, `plan-update`, `plan-close`) — one symlink per skill.

```bash
mkdir -p ~/.agents/skills

# Single-skill plugins
for plugin in ship pr tech-writer deck roadmap diagram; do
  ln -sfn "$HOME/.codex/plugins/mikersays/mikersays-plugins/plugins/$plugin/skills/$plugin" \
    "$HOME/.agents/skills/$plugin"
done

# plan ships five skills
for skill in plan-init plan-add plan-list plan-update plan-close; do
  ln -sfn "$HOME/.codex/plugins/mikersays/mikersays-plugins/plugins/plan/skills/$skill" \
    "$HOME/.agents/skills/$skill"
done
```

Symlinks mean the skills stay in sync with the repo automatically — no extra copy step needed on update.

### Step 4: Install the startup hook

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

### Step 4b: Enable plugins in config.toml

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

[plugins."plan@mikersays-marketplace"]
enabled = true
```

### Step 5: Verify

Run the following checks and report the result for each:

1. `ls ~/.codex/plugins/mikersays/mikersays-plugins/.codex-plugin/marketplace.json` — confirm repo is present
2. `cat ~/.agents/plugins/marketplace.json` — confirm marketplace entry exists
3. `cat ~/.codex/hooks.json` — confirm SessionStart hook is present
4. `git -C ~/.codex/plugins/mikersays/mikersays-plugins log --oneline -1` — show the installed commit
