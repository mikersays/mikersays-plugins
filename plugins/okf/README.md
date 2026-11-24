# okf

Author, index, and validate **Open Knowledge Format** (OKF v0.3) bundles from inside Claude Code
or Codex CLI. OKF is a vendor-neutral format, started by Google Cloud, for knowledge that humans
and agents share: a directory of Markdown files with YAML frontmatter, where provenance (`sources`), trust
(`generated`, `verified`), lifecycle (`status`, `stale_after`), and sanctioned computations
(`Attested Computation`) are first-class frontmatter instead of tribal knowledge.

Spec: <https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md> (v0.3,
released 2026-11-18; the old `GoogleCloudPlatform/open-knowledge-format` repository is deprecated).
A condensed working copy the skills read lives at [`references/okf-spec.md`](references/okf-spec.md),
and it ends with the steps to migrate a v0.2 bundle.

## Commands

| Command | What it does |
|---|---|
| `/okf-init [dir] [scope]` | Bootstrap a bundle: a root `index.md` with `okf_version`, `title`, `description`, and `license`, a `log.md`, and, when asked, concepts seeded from an inventory of the repo (schemas, APIs, dbt models, runbooks). |
| `/okf-new [type] [title] [from:<file\|url>] [in:<subdir>]` | Author one concept with honest frontmatter: your agent as `generated.by`, `status: draft`, `sources` for what was read, footnotes keyed to source ids, never a fabricated `verified`. Handles Attested Computations (`runtime`, `parameters`, `executor`, `attester`) and retiring a concept with `superseded_by`. Refreshes `index.md` and `log.md`. |
| `/okf-index [dir]` | Regenerate every `index.md` from frontmatter, keeping the root's bundle metadata and hand-written descriptions where a concept has none. |
| `/okf-validate [dir] [--strict]` | Conformance (§11) plus lint: bad timestamps and actor ids, duplicate keys, footnotes without a source, broken links and path fields, stale concepts, verifications older than the last change, weak computation contracts, indexes out of sync, v0.2 paths to migrate. Reports trust tiers and status counts. |

## What a concept looks like

```markdown
---
type: BigQuery Table
title: Customer Orders
description: One row per completed customer order across all channels.
resource: https://console.cloud.google.com/bigquery?p=acme&d=sales&t=orders
tags: [sales, orders]
generated: { by: claude-code/claude-opus-5-5, at: "2026-09-19T10:00:00Z" }
verified: { by: "human:kliu", at: "2026-09-20T09:00:00Z" }
status: stable
stale_after: "2026-12-31T00:00:00Z"
sources:
  - id: warehouse-ddl
    resource: /references/ddl/orders.sql
    title: Sales warehouse DDL
    last_modified: "2026-08-02T14:11:00Z"
---

# Schema

| Column | Type | Description |
|---|---|---|
| `order_id` | STRING | Globally unique order id.[^warehouse-ddl] |
| `customer_id` | STRING | FK into [customers](customers.md).[^warehouse-ddl] |

[^warehouse-ddl]: Sales warehouse DDL
```

The trust model is the point: `generated` says who wrote it, `verified` says who confirmed it,
and consumers derive a tier (unverified → machine-confirmed → human-reviewed) from the `human:`
prefix. Since v0.3, only verifications at or after `generated.at` count, so a concept that an agent
rewrites after a human review is no longer human-reviewed until someone confirms it again. The
skills never write `verified` on their own output. Only a person confirming in conversation earns a
`human:<id>` entry.

## The script

`scripts/okf.py` is stdlib-only Python 3.9+ with a built-in YAML-subset parser (PyYAML is used
only as a fallback when present). The two mechanical skills call it; you can too:

```bash
python3 scripts/okf.py validate path/to/bundle [--strict] [--json] [--now 2026-09-19T00:00:00Z]
python3 scripts/okf.py index    path/to/bundle [--write | --check]
python3 scripts/okf.py log      path/to/bundle "Added the orders table." --kind Creation
python3 scripts/okf.py --selftest
```

`validate` exits 1 on conformance errors (or on warnings with `--strict`); `index --check` exits 1
when any `index.md` is stale, so you can run both commands in CI. Run against the four v0.3 sample bundles in the
upstream repo (`acme_retail`, `ga4`, `stackoverflow`, `crypto_bitcoin`), `validate` reports all four
as conformant with no warnings. For a bundle that declares `okf_version` 0.2 or earlier, or no
version, it applies the spec's v0.2 fallbacks and flags what to change before you declare 0.3.

## Why a plugin for this

- **Agents write most of the corpus now.** The format exists so that a machine-maintained
  knowledge base stays trustable; the skills enforce the honesty rules the spec relies on (real
  sources, real actors, no invented verification, no positional footnotes).
- **Bundles are just files in git.** Diffs, blame, PRs, and `grep` all work. No service, no SDK.
- **Progressive disclosure.** `index.md` at every level lets an agent open one directory at a
  time instead of loading everything into context; `okf-index` keeps those listings truthful.
- **Attested computations.** A metric can carry the sanctioned SQL, the parameters an agent may
  bind, and the code that checks a run, so "was this number produced the way we said" is a
  mechanical comparison rather than a judgment call.

## Layout

```
plugins/okf/
  references/okf-spec.md        ← condensed v0.3 spec every skill reads, with v0.2 migration steps
  scripts/okf.py                ← validate / index / log / --selftest
  skills/okf-init/SKILL.md
  skills/okf-new/SKILL.md
  skills/okf-index/SKILL.md
  skills/okf-validate/SKILL.md
```
