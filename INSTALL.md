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
- `monograph` — Build a multi-page PhD-level GitHub Pages site on any topic — research, free-licensed photography, a distinctive topic-tuned design, all built by a team of parallel expert subagents and shipped to docs/
- `bootcamp` — Spin up a swarm of expert subagents to build an interactive zero-to-hero course site on any topic — progressive modules, worked examples, exercises with solutions, checkpoints, a capstone, and progress tracking — shipped to docs/ and deployed on GitHub Pages
- `plan` — Lightweight markdown-based tracker for bugs/features/chores/todos that lives in docs/plan/ inside your repo
- `issues` — Per-issue bug/feature/incident tracker in docs/issues/ — one file per ticket with symptom/repro/root cause/fix/verification, branch-on-start, and a hard rule to align with the user before implementing
- `handoff` — Audit session context and persist what matters for the next agent — decisions, dead ends, insights, and in-flight work
- `slop` — Rewrite any text to maximally overuse every known AI-writing tell — em-dashes, the rule of three, "not X but Y", and the rest
- `gh-pages` — Build or publish a static site on GitHub Pages — saves the site to docs/ and enables Pages from the docs/ folder on the default branch

## Quick install (native)

Current Codex CLI uses two commands: first add the marketplace, then install each plugin you want:

```bash
codex plugin marketplace add mikersays/mikersays-plugins
codex plugin add ship@mikersays-plugins
```

Repeat `codex plugin add <plugin>@mikersays-plugins` for each plugin you want. The rest of this document is the manual installer — use it if the native command is not available or you need fine-grained control.

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

Read the file if it exists and inspect its root structure, then follow the matching case. Codex expects this file to be a single marketplace object with a `plugins[]` array.

**Case A — file does not exist:**
Create `~/.agents/plugins/` if needed, then write the mikersays marketplace object:
```json
<mikersays-marketplace>
```

**Case B — file exists and root is a JSON object (`{...}`):**
If the object's `"name"` is `"mikersays-marketplace"`, replace its `plugins[]` array with the plugin list below while preserving any extra top-level fields. If it has a different `"name"`, stop and tell the user the personal marketplace file already belongs to another marketplace; use the native `codex plugin marketplace add mikersays/mikersays-plugins` flow instead.

**Case C — file exists and root is a legacy JSON array (`[...]`):**
Find the element whose `"name"` is `"mikersays-marketplace"` and convert that object into the file root after applying the plugin list below. If there is no such element, stop and tell the user the existing file uses an old multi-marketplace format that needs manual migration or the native `codex plugin marketplace add mikersays/mikersays-plugins` flow.

For a new file, the full mikersays marketplace object is:

```json
{
  "name": "mikersays-marketplace",
  "interface": {
    "displayName": "mikersays Plugins"
  },
  "plugins": [
    {
      "name": "ship",
      "source": { "source": "local", "path": "./.codex/plugins/mikersays/mikersays-plugins/plugins/ship" },
      "policy": { "installation": "INSTALLED_BY_DEFAULT", "authentication": "ON_INSTALL" },
      "category": "Developer Tools"
    },
    {
      "name": "pr",
      "source": { "source": "local", "path": "./.codex/plugins/mikersays/mikersays-plugins/plugins/pr" },
      "policy": { "installation": "INSTALLED_BY_DEFAULT", "authentication": "ON_INSTALL" },
      "category": "Developer Tools"
    },
    {
      "name": "tech-writer",
      "source": { "source": "local", "path": "./.codex/plugins/mikersays/mikersays-plugins/plugins/tech-writer" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_USE" },
      "category": "Writing"
    },
    {
      "name": "deck",
      "source": { "source": "local", "path": "./.codex/plugins/mikersays/mikersays-plugins/plugins/deck" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_USE" },
      "category": "Productivity"
    },
    {
      "name": "roadmap",
      "source": { "source": "local", "path": "./.codex/plugins/mikersays/mikersays-plugins/plugins/roadmap" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    },
    {
      "name": "diagram",
      "source": { "source": "local", "path": "./.codex/plugins/mikersays/mikersays-plugins/plugins/diagram" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    },
    {
      "name": "monograph",
      "source": { "source": "local", "path": "./.codex/plugins/mikersays/mikersays-plugins/plugins/monograph" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_USE" },
      "category": "Productivity"
    },
    {
      "name": "bootcamp",
      "source": { "source": "local", "path": "./.codex/plugins/mikersays/mikersays-plugins/plugins/bootcamp" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_USE" },
      "category": "Productivity"
    },
    {
      "name": "plan",
      "source": { "source": "local", "path": "./.codex/plugins/mikersays/mikersays-plugins/plugins/plan" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    },
    {
      "name": "issues",
      "source": { "source": "local", "path": "./.codex/plugins/mikersays/mikersays-plugins/plugins/issues" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    },
    {
      "name": "handoff",
      "source": { "source": "local", "path": "./.codex/plugins/mikersays/mikersays-plugins/plugins/handoff" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    },
    {
      "name": "slop",
      "source": { "source": "local", "path": "./.codex/plugins/mikersays/mikersays-plugins/plugins/slop" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Writing"
    },
    {
      "name": "gh-pages",
      "source": { "source": "local", "path": "./.codex/plugins/mikersays/mikersays-plugins/plugins/gh-pages" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Developer Tools"
    }
  ]
}
```

### Step 3: Symlink skills into ~/.agents/skills

Codex's `/skills` command scans `~/.agents/skills/`. Create symlinks there so all skills appear.

`ship`, `pr`, `tech-writer`, `deck`, `roadmap`, `diagram`, `monograph`, `bootcamp`, `handoff`, `slop`, and `gh-pages` each ship a single same-named skill — one symlink per plugin. The `plan` plugin ships five skills (`plan-init`, `plan-add`, `plan-list`, `plan-update`, `plan-close`); the `issues` plugin ships four (`issue-init`, `issue-new`, `issue-start`, `issue-close`) — one symlink per skill.

```bash
mkdir -p ~/.agents/skills

# Single-skill plugins
for plugin in ship pr tech-writer deck roadmap diagram monograph bootcamp handoff slop gh-pages; do
  ln -sfn "$HOME/.codex/plugins/mikersays/mikersays-plugins/plugins/$plugin/skills/$plugin" \
    "$HOME/.agents/skills/$plugin"
done

# plan ships five skills
for skill in plan-init plan-add plan-list plan-update plan-close; do
  ln -sfn "$HOME/.codex/plugins/mikersays/mikersays-plugins/plugins/plan/skills/$skill" \
    "$HOME/.agents/skills/$skill"
done

# issues ships four skills
for skill in issue-init issue-new issue-start issue-close; do
  ln -sfn "$HOME/.codex/plugins/mikersays/mikersays-plugins/plugins/issues/skills/$skill" \
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

[plugins."monograph@mikersays-marketplace"]
enabled = true

[plugins."bootcamp@mikersays-marketplace"]
enabled = true

[plugins."plan@mikersays-marketplace"]
enabled = true

[plugins."issues@mikersays-marketplace"]
enabled = true

[plugins."handoff@mikersays-marketplace"]
enabled = true

[plugins."slop@mikersays-marketplace"]
enabled = true

[plugins."gh-pages@mikersays-marketplace"]
enabled = true
```

### Step 5: Verify

Run the following checks and report the result for each:

1. `ls ~/.codex/plugins/mikersays/mikersays-plugins` — confirm the cloned repo is present
2. `cat ~/.agents/plugins/marketplace.json` — confirm marketplace entry exists
3. `cat ~/.codex/hooks.json` — confirm SessionStart hook is present
4. `grep -c 'mikersays-marketplace' ~/.codex/config.toml` — confirm plugin entries in config.toml
5. `git -C ~/.codex/plugins/mikersays/mikersays-plugins log --oneline -1` — show the installed commit
