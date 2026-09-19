---
name: okf-new
description: Author a new Open Knowledge Format (OKF v0.2) concept — a markdown document with YAML frontmatter describing a table, dataset, API, metric, playbook, policy, reference, or an Attested Computation with runtime, parameters, executor, and attester — with provenance (sources, footnotes), trust (generated, verified), and lifecycle (status, stale_after) fields filled honestly, then refresh index.md and log.md. Trigger on "okf new", "add a concept", "document this table as OKF", "write an OKF doc for X", "add X to the knowledge bundle", "capture this metric definition", or "make an attested computation".
argument-hint: "[type] [title] [from:<file|url>] [in:<subdir>] [resource:<uri>] [tags:a,b] [status:draft|stable]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch, AskUserQuestion
---

# okf-new — author a concept

Write one OKF concept document, honestly sourced, and wire it into the bundle.
Read `../../references/okf-spec.md` (plugin root, relative to this skill) first; it is the
condensed spec, including the exact frontmatter families and the Attested Computation contract.

## Find the bundle

The bundle root is the directory whose `index.md` frontmatter carries `okf_version`, or failing
that, the nearest directory tree whose `.md` files carry `type:` frontmatter. If the user named
one in `$ARGUMENTS` (`in:` or a path), use it. If none exists, initialize one the way
`../okf-init/SKILL.md` describes and mention that you did. If several exist, ask.

## Decide what you are writing

From `$ARGUMENTS` and the conversation, settle four things:

- **Type.** Free-form but descriptive: `BigQuery Table`, `Postgres Table`, `API Endpoint`,
  `Service`, `Metric`, `Playbook`, `Policy`, `Reference`, `Skill`, `Attested Computation`.
  Match the types already used in this bundle before inventing a new one.
- **Location and filename.** Put it with its siblings (`tables/orders.md`, `metrics/revenue.md`).
  Kebab-case slug of the title. `index.md` and `log.md` are reserved and never concept names.
- **Bound to a resource or not.** A table, API, or dashboard gets a `resource:` URI (console link,
  repo path, endpoint). A metric, policy, or playbook does not.
- **Where the content comes from.** `from:<file|url>` or whatever the user pointed at: a schema
  file, a migration, a spec, a wiki page, a SQL query, or just the conversation. Read it; do not
  describe what you have not looked at.

Ask only when a wrong guess would produce the wrong document: an ambiguous type, no idea where
the truth lives, or a metric whose definition you would have to invent.

## Write the frontmatter honestly

```yaml
---
type: BigQuery Table
title: Customer Orders
description: One sentence; index.md and previews use it.
resource: https://console.cloud.google.com/bigquery?p=acme&d=sales&t=orders   # only when bound
tags: [sales, orders]
generated: { by: claude-code/<model id>, at: <now, UTC> }
status: draft
sources:
  - id: warehouse-schema
    resource: schemas/sales/orders.sql          # what you actually read
    title: Sales warehouse DDL
    last_modified: <git log -1 --format=%cI on that file, if in git>
---
```

- `generated.by` is your own actor id in `<producer>/<version>` form (`claude-code/<model id>`
  in Claude Code, `codex-cli/<model>` in Codex). `generated.at` is `date -u +%Y-%m-%dT%H:%M:%SZ`.
- `status: draft` unless the user says the content is settled. `stable` is a claim.
- **Never write `verified`.** A human saying "yes, that's right" in the conversation is the one
  case that earns `verified: { by: human:<their id>, at: <now> }`; ask which id they want
  (git `user.name`, email local part, or a handle) rather than inventing one.
- One `sources` entry per thing you derived content from, with an `id` whenever the body cites it.
  Fill `author`, `usage_count`, `last_modified` only from real data (git history, a catalog, a
  page's byline). Never guess a usage count; never write `usage_count` without `usage_window`.
- `stale_after` only when there is a real review cadence to point at (an annual policy, a quarterly
  schema review). Absent is better than arbitrary.
- Keep any extra keys the bundle's other concepts use (`owner`, `domain`, `not:` …); consistency
  within a bundle matters more than the spec's minimum.

## Write the body

Structure over prose. Use what the type calls for:

- **Tables, datasets, APIs:** `# Schema` as a table of column/field, type, description, with a
  footnote on each row taken from a source. Then joins, grain, gotchas (`# Notes for consumers`),
  and `# Examples` with fenced queries. Say what the grain is; that is the thing new readers get
  wrong.
- **Metrics:** `# Definition` in words and as a formula, what it is *not* (a common confusion),
  and a link to the Attested Computation that produces it if one exists or should.
- **Playbooks:** trigger, steps, escalation, with links to the concepts each step touches.
- **Policies and references:** the substance, plus a `# Cited by` list if you know the consumers.

Link generously. `[customers](/tables/customers.md)` bundle-relative links are the recommended
form; a link to a concept that does not exist yet is allowed and tells the reader what to write
next. Cite claims with footnotes keyed to `sources[].id` (`[^warehouse-schema]`), and close the
body with the footnote definitions. Never use positional labels like `[^1]`.

## Attested Computation specifics

Only when the concept's job is to produce a number the sanctioned way. Then:

- `runtime:` is required (`bigquery`, `postgres`, `dbt`, `python`, …) and defines what
  `parameters` mean.
- `parameters:` lists every hole an agent may fill: `{ name, type, required }`. Bind variables in
  the computation (`@year`, `{{ var('year') }}`) must match those names.
- The computation goes in **one** place: a single fence under `# Computation`, or a file named by
  `computation:`. Short SQL inline; long or shared SQL as a file under `references/`.
- `executor.resource` points at run instructions (a Skill doc in the bundle is the usual shape) and
  `executor.receipt` lists the evidence fields a run returns (`job_id`, `executed_sql`, `result`).
- `attester.resource` points at deterministic, no-LLM code that checks a receipt. If none exists,
  write the concept without `attester` and say so in the report; do not point at a file you did
  not create.
- The metric that uses the value is a separate concept that links here.

## Wire it in

Update the directory's `index.md` and the bundle `log.md` with the bundled script rather than by
hand, so descriptions stay in sync with frontmatter:

```bash
OKF="${CLAUDE_PLUGIN_ROOT}/scripts/okf.py"
[ -f "$OKF" ] || OKF="$(find ~/.claude/plugins ~/.codex/plugins -path '*/okf/scripts/okf.py' -print -quit 2>/dev/null)"
python3 "$OKF" index "<bundle>" --write
python3 "$OKF" log "<bundle>" "Added [<title>](/<path>.md)." --kind Creation
python3 "$OKF" validate "<bundle>"
```

Fix anything `validate` reports on the file you just wrote. Then report the path, the type, what
you sourced it from, what you inferred, and that it is `draft` and unverified until someone
confirms it. Do not commit.
