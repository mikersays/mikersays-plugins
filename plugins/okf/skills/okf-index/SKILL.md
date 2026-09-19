---
name: okf-index
description: Regenerate every index.md in an Open Knowledge Format (OKF) bundle from concept frontmatter — subdirectories first, then one section per type, entries with descriptions — keeping hand-written descriptions where frontmatter has none. Trigger on "okf index", "rebuild the index", "regenerate index.md", "the index is out of date", or "update the bundle listing".
argument-hint: "[bundle directory]"
allowed-tools: Bash, Read, Edit, Glob
---

# okf-index — regenerate index files

`index.md` files exist for progressive disclosure: a reader or agent sees what a directory holds
before opening anything. They rot the moment a concept is added, renamed, or re-described, so
regenerate them from frontmatter rather than editing by hand.

## Run

Locate the bundle (the directory whose `index.md` frontmatter carries `okf_version`, or the one
the user named), then:

```bash
OKF="${CLAUDE_PLUGIN_ROOT}/scripts/okf.py"
[ -f "$OKF" ] || OKF="$(find ~/.claude/plugins ~/.codex/plugins -path '*/okf/scripts/okf.py' -print -quit 2>/dev/null)"
python3 "$OKF" index "<bundle>"            # dry run: unified diff per index.md
python3 "$OKF" index "<bundle>" --write    # apply
python3 "$OKF" index "<bundle>" --check    # exit 1 if anything is stale (CI-friendly)
```

If `find` returns nothing the plugin is not installed where expected; report that and stop.

## What the generator does

- One `index.md` per directory that contains concepts or leads to them, root included.
- Root index keeps its existing frontmatter, or gains `okf_version: "0.2"` if it had none. No other
  index carries frontmatter.
- Sections: `# Subdirectories` first, then one `# <Type>` section per concept type, entries sorted
  by title as `* [Title](file.md) - description`.
- Descriptions come from each concept's `description`. When a concept has none, the description
  already in the old index is kept, so hand-written text survives. Subdirectory descriptions are
  always preserved; a new subdirectory gets a count-and-types placeholder.
- A directory holding only code or assets (an `attesters/` folder) keeps its existing heading and
  lists the files.

## Judgment

Read the dry-run diff before writing. Two things are worth a human sentence rather than a silent
apply:

- A subdirectory placeholder like `3 concepts (Metric, Policy)`: replace it with a real one-line
  description in the generated file after writing, or better, tell the user what it is.
- Entries whose description changed because the concept's `description` was edited: expected.
  Entries whose description vanished: the concept has no `description`; add one to the concept
  (that is the fix) rather than to the index.

Do not commit. Report which index files changed and anything that needs a human description.
