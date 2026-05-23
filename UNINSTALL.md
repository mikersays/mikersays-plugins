# mikersays-plugins — Codex Uninstaller

This page removes everything the mikersays installer placed on the current machine.

## What gets removed

- Repo at `~/.codex/plugins/mikersays/mikersays-plugins`
- Skill symlinks from `~/.agents/skills/`: `ship`, `pr`, `tech-writer`, `deck`, `roadmap`, `diagram`, `monograph`, `plan-init`, `plan-add`, `plan-list`, `plan-update`, `plan-close`, `issue-init`, `issue-new`, `issue-start`, `issue-close`
- `mikersays-marketplace` entry from `~/.agents/plugins/marketplace.json`
- `mikersays` plugin entries from `~/.codex/config.toml`
- `SessionStart` git-pull hook from `~/.codex/hooks.json`

No other marketplaces, skills, or config entries are touched.

## Prompt to give Codex

```
Read @UNINSTALL.md and follow the instructions exactly to uninstall the mikersays-plugins marketplace from this machine. Update the local marketplace file, config, and hooks without affecting any other entries, verify the removal, and tell me the final result.
```

## Headless one-liner

```bash
curl -sL https://raw.githubusercontent.com/mikersays/mikersays-plugins/master/UNINSTALL.md \
  | codex exec --full-auto --add-dir ~/.codex --add-dir ~/.agents --skip-git-repo-check -
```

---

## Instructions for Codex

> **Important:** These steps write to `~/.codex` and `~/.agents`. The headless command uses `--add-dir` to grant write access to exactly those two directories.

### Step 1: Remove the repo

```bash
rm -rf ~/.codex/plugins/mikersays/mikersays-plugins
```

If `~/.codex/plugins/mikersays/` is now empty, remove it too:

```bash
rmdir ~/.codex/plugins/mikersays 2>/dev/null || true
```

### Step 2: Remove skill symlinks

```bash
for skill in ship pr tech-writer deck roadmap diagram monograph plan-init plan-add plan-list plan-update plan-close issue-init issue-new issue-start issue-close; do
  rm -f ~/.agents/skills/$skill
done
```

If `~/.agents/skills/` is now empty, remove it too:

```bash
rmdir ~/.agents/skills 2>/dev/null || true
```

### Step 3: Update marketplace.json

Target file: `~/.agents/plugins/marketplace.json`

If the file does not exist, skip this step.

Read the file and inspect its root structure:

**Case A — root is a JSON array (`[...]`):**
Remove the element whose `"name"` is `"mikersays-marketplace"` and write the remaining array back. If the array is now empty, write `[]`. If only one element remains, keep it as an array (do not unwrap to an object).

**Case B — root is a JSON object (`{...}`):**
If the object's `"name"` is `"mikersays-marketplace"`, delete the file entirely. Otherwise, leave the file untouched.

### Step 4: Update config.toml

Target file: `~/.codex/config.toml`

If the file does not exist, skip this step.

Remove these lines (and the blank line following each block) if present:

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

[plugins."plan@mikersays-marketplace"]
enabled = true

[plugins."issues@mikersays-marketplace"]
enabled = true
```

Do not modify any other lines in the file.

### Step 5: Update hooks.json

Target file: `~/.codex/hooks.json`

If the file does not exist, skip this step.

Read the file. Find the `SessionStart` array and remove any handler object whose `"command"` contains the string `mikersays`. Write the updated file back.

- If the `SessionStart` array is now empty, remove the `SessionStart` key.
- If `hooks` is now an empty object, write `{ "hooks": {} }`.
- If the file would be `{ "hooks": {} }` and that was the original content, delete the file entirely.

### Step 6: Verify

Run the following checks and report the result for each:

1. `ls ~/.codex/plugins/mikersays 2>/dev/null || echo "removed"` — confirm repo directory is gone
2. `ls ~/.agents/skills/ship 2>/dev/null || echo "removed"` — confirm skill symlinks are gone
3. Check `~/.agents/plugins/marketplace.json` does not contain `mikersays-marketplace`
4. Check `~/.codex/config.toml` does not contain `mikersays-marketplace`
5. Check `~/.codex/hooks.json` does not contain `mikersays`
