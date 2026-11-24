---
name: okf-init
description: Bootstrap an Open Knowledge Format (OKF v0.3) knowledge bundle — a directory of Markdown concepts with YAML frontmatter, a root index.md that declares the version and describes the bundle, and a log.md — optionally seeded from an inventory of the repo's tables, APIs, services, metrics, or runbooks. Trigger on "okf init", "start a knowledge bundle", "create an OKF bundle", "set up open knowledge format", "document this repo as OKF", or "make a knowledge base for agents".
argument-hint: "[bundle directory] [what the bundle should cover]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion
---

# okf-init — bootstrap a knowledge bundle

Create the skeleton of an OKF bundle, and when asked, seed it with concepts drawn from the repo.
Read `../../references/okf-spec.md` (plugin root, relative to this skill) before writing anything;
it is the condensed spec and every skill in this plugin works from it.

## Where the bundle lives

Look before you create. A bundle already exists if some directory holds an `index.md` whose
frontmatter carries `okf_version`, or a cluster of `.md` files whose frontmatter starts with
`type:`. If one exists, point the user at it and stop, and use `/okf-new` from here. If it
declares `okf_version` 0.2 or earlier, offer to migrate it with the steps at the end of the spec
reference.

Otherwise pick a location:

- What the user named in `$ARGUMENTS` wins.
- Else use the repo's own conventions: an existing `docs/` or `knowledge/` area, or the pattern
  the upstream reference uses, `bundles/<name>/`.
- Else default to `knowledge/` at the repo root and say so.

Never nest the bundle inside an unrelated docs tree without asking; a bundle is a unit of
distribution and should be trivially tarballable.

## What to create

The minimum viable bundle is two files. Add subdirectories only when you know what goes in them.

The root `index.md` is the only index that may have frontmatter. It carries the bundle metadata (§8.1):

```markdown
---
okf_version: "0.3"
title: <display name of the bundle>
description: <what the bundle covers>. Use it for <the questions it answers>.
license: <SPDX id such as CC-BY-4.0, or a path such as /LICENSE.md; omit if unknown>
---

# Subdirectories

* [tables](tables/index.md) - <one line>
```

The `description` is how an agent that sees many bundles picks this one, so say when to use it.
Ask about `license` only if the repo has no license file to point at; never guess one.

`log.md`, newest first, ISO date headings:

```markdown
# Update Log

## <today, YYYY-MM-DD>
* **Initialization**: Created the <name> bundle (OKF v0.3).
```

`log.md` has no frontmatter, and neither does any `index.md` below the root.

Group subdirectories the way the knowledge actually splits: by concept type (`tables/`, `metrics/`,
`playbooks/`, `computations/`, `policies/`), by system, or by domain. Plural kebab-case names.
A `references/` directory is the conventional home for mirrored external material, executor
instructions, and attester code. Don't scaffold empty directories "for later". A `README.md` or
`AGENTS.md` without `type` frontmatter may sit in the bundle; OKF skips it (§3.2).

The bundled script can regenerate every `index.md` from frontmatter and append log entries; use it
rather than hand-editing once concepts exist:

```bash
OKF="${CLAUDE_PLUGIN_ROOT}/scripts/okf.py"
[ -f "$OKF" ] || OKF="$(find ~/.claude/plugins ~/.codex/plugins -path '*/okf/scripts/okf.py' -print -quit 2>/dev/null)"
python3 "$OKF" index "<bundle>" --write
python3 "$OKF" log "<bundle>" "Created the bundle" --kind Initialization
```

## Seeding from the repo

When the user asks to document the codebase (or the argument names a scope like "our BigQuery
datasets" or "the public API"), do an inventory first and agree on the shape before writing
concepts:

1. Find the knowledge-bearing artifacts: schema files, migrations, OpenAPI specs, dbt models,
   service definitions, runbooks, ADRs, metric definitions in SQL or dashboards.
2. Propose a directory layout and a concept list (type + title + one-line description each).
   Ask which to include if the list is long or the scope is fuzzy.
3. Author the agreed concepts following the rules in `../okf-new/SKILL.md`: one concept per
   file, `generated.by` set to your own actor id, `status: draft`, `sources` pointing at the files
   you read, footnotes on claims you took from them, no `verified` entries.
4. Run `index --write`, log the initialization, then `validate` (see `../okf-validate/SKILL.md`).

Scale the effort to the ask. "Init a bundle" is two files and a sentence. "Document the warehouse"
is an inventory, a conversation, and a batch of concepts.

## Guardrails

- Never write `verified` on anything you generated; a human confirming in conversation is the only
  thing that earns a `human:<id>` entry, and the person must say so explicitly.
- `okf_version` and the other bundle metadata go in the root `index.md` only. No frontmatter on any
  other index or on `log.md`.
- Quote `okf_version: "0.3"`, timestamps, and `<scheme>:<id>` actors.
- Timestamps are RFC 3339 date-times with an offset (`date -u +%Y-%m-%dT%H:%M:%SZ`).
- Don't commit. Report what was created, where, and that `/okf-new` adds concepts.
