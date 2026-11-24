# Open Knowledge Format v0.3: working reference

Condensed from the normative spec at
<https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md> (released
2026-11-18). Section numbers (§) refer to that document. The old repository,
`GoogleCloudPlatform/open-knowledge-format`, is deprecated and still holds v0.2. Read the full spec
when something here is ambiguous.

OKF represents *knowledge* (the metadata, context, and curated insight about data and systems) as a
directory of Markdown files with YAML frontmatter. It has no schema registry, no central authority,
and no required tools. People, agents, and export pipelines produce it. Agents, UIs, search
indexes, and plain code consume it. It makes five things first-class: provenance, trust,
freshness, lifecycle, and attestation.

## Vocabulary (§2)

| Term | Meaning |
|---|---|
| **Bundle** | A self-contained directory tree of knowledge documents. The unit of distribution (git repo, tarball, or subdirectory of a larger repo). |
| **Bundle root** | The top directory of a bundle. Paths that start with `/` resolve from it. A bundle-root `index.md` with frontmatter marks it inside a larger repo. |
| **Concept** | One Markdown document that is one unit of knowledge: a table, an API, a metric, a playbook, a policy, a computation. See §3.2 for what counts. |
| **Concept ID** | The file path in the bundle with `.md` removed: `tables/orders`. |
| **Asset** | Any file whose name does not end in `.md` (images, attester code). Not a concept. |
| **Link** | A standard Markdown link. An untyped, directed relationship; the prose says which kind. Only the directory tree gives parent/child structure. |
| **Path field** | A frontmatter field whose value is a path or URI (§6.2). |
| **Source** | Material a concept derives from, recorded in `sources`. |
| **Actor** | Who or what did something (§7): `<producer>/<version>` or `<scheme>:<id>`. |
| **Trust tier** | Calculated from the *current* `verified` events: unverified, machine-confirmed, or human-reviewed (§5.3). |
| **Attested Computation** | A concept with a sanctioned way to compute a value, plus the means to check a run of it (§10). |
| **Extension key** | A frontmatter key the spec does not define (§4.1). |

## Bundle layout (§3)

```
bundle/
  index.md            # optional; directory listing, and bundle metadata at the root (§8)
  log.md              # optional; dated change history, newest first (§9)
  <concept>.md
  <asset>             # optional; image, code, or other non-Markdown file
  <group>/            # any grouping: tables/, metrics/, playbooks/, computations/ ...
    index.md
    <concept>.md
```

- `index.md` and `log.md` are **reserved** at every level. They are never concepts, whatever their
  frontmatter says.
- Directory structure is the producer's choice. A `references/` directory is a naming convention for
  copies of external material, run instructions, and executor or attester code (§6.3). It is not a
  requirement.
- Tags live in frontmatter (`tags`). OKF has no tag file format.

### What is a concept (§3.2)

1. A `.md` file that is not reserved and whose frontmatter has a non-empty `type` is a concept.
2. A `.md` file with no frontmatter, or no `type`, is **not** a concept. Consumers skip it, and it
   does not affect conformance. Validators SHOULD warn. This lets a bundle hold `README.md`,
   `AGENTS.md`, `CONTRIBUTING.md`, and `SKILL.md`.
3. A file whose name does not end in `.md` is an asset. A link or path field may point at it.
4. Files and directories whose names start with `.` are not part of the bundle.
5. Consumers read only files under the bundle root and do not follow symbolic links out of it.

## Concept document (§4)

```markdown
---
type: <Type name>                      # REQUIRED; the only always-required key
title: <display name>                  # optional; consumers may derive one from the filename
description: <one sentence>            # optional; index.md entries, previews, search snippets use it
resource: <canonical URI of the asset> # optional; only for concepts bound to a real asset
tags: [a, b]                           # optional
# provenance, trust, lifecycle families (§5); computation fields (§10); extension keys
---

<Markdown body>
```

**Frontmatter syntax (§4).**

- The file MUST start with a line that is exactly `---`. The block ends at the next line that is
  exactly `---`.
- The frontmatter MUST parse as a YAML 1.2 mapping with the core schema.
- Producers MUST NOT write duplicate keys. Consumers MAY reject them.
- Producers SHOULD quote values that look like numbers or booleans: `okf_version: "0.3"`.
- Producers SHOULD NOT use custom YAML tags.
- When you modify a file, do not re-serialize values you did not change. This keeps diffs small.

**`type`** is free-form: `BigQuery Table`, `API Endpoint`, `Metric`, `Playbook`, `Policy`,
`Reference`, `Skill`, `Attested Computation`. No registry exists. Consumers MUST accept unknown
types. A concept with only `type` is fully conformant.

**Extension keys (§4.1).** Producers MAY add keys at any level, including inside `sources` entries,
`generated`, `verified` entries, `executor`, and `attester`. Consumers MUST NOT reject unknown keys.
A producer that modifies a file MUST keep the keys it does not know. Future OKF versions will never
define keys that start with `x-`, so name your own keys `x-<producer>-<name>`, for example
`x-acme-owner`.

**Body (§4.2).** CommonMark, with GFM tables and `[^label]` footnotes. Do not depend on other
extensions. No sections are required. Conventional headings: `# Schema` (columns or fields),
`# Examples` (fenced code), `# Computation` (Attested Computation only). To attribute a claim, use a
footnote keyed to a `sources[].id`. Do not write a citations list in the body.

## Provenance, trust, lifecycle (§5)

All families are optional. A consumer never rejects a concept that lacks them.

**Timestamps.** The timestamp keys are `generated.at`, `verified[].at`, `stale_after`,
`sources[].last_modified`, `usage_window.from`, and `usage_window.to`. Each value has one of two
RFC 3339 forms, and no other form is valid:

| Form | Example | Meaning |
|---|---|---|
| Date-time with an offset | `"2026-06-30T14:00:00Z"` | That instant. |
| Date only | `"2026-06-30"` | The start of that day in UTC. |

- A date-time without an offset (`2026-06-30T14:00:00`) is invalid.
- Consumers accept quoted strings and YAML-native timestamps. Quote them anyway.
- Use the date-time form for `generated.at` and `verified[].at`, because consumers compare them
  (§5.3). A date-only `verified.at` is midnight UTC, which is *earlier* than a same-day
  `generated.at`, so the event does not count.

### `sources` (§5.1)

```yaml
sources:
  - id: ga4-schema                     # stable key; SHOULD be present when the body cites it
    resource: https://.../export-schema  # REQUIRED in an entry: URL, bundle path, or scope descriptor
    title: GA4 BigQuery Export schema
    author: "team:ga4-docs"            # an actor (§7); authority signal
    usage_count: 5000                  # uses of the resource during usage_window; liveness signal
    last_modified: "2026-05-30T00:00:00Z"  # when the SOURCE changed (not generated.at)
usage_window: { from: "2026-06-01T00:00:00Z", to: "2026-06-30T00:00:00Z" }   # frames every usage_count
```

- `resource` is a concrete artifact (URL or bundle path) or a scope descriptor that a consumer cannot
  follow, such as `all queries in BigQuery project X`.
- One entry MAY carry its own `usage_window`, which then applies to that entry only.
- OKF records credibility **signals**, never a score. `usage_count` is coarse: read it as
  alive-or-dead and trend, not as a ranking.
- Lineage is expressed through links and path fields. A `resource` that points at another concept is
  already an edge in the bundle graph (§6.4). OKF has no `derived_from` field.
- **Per-claim attribution** uses a footnote whose label is a `sources[].id`:

  ```markdown
  The `events_` table is sharded daily as `events_YYYYMMDD`.[^ga4-schema]

  [^ga4-schema]: GA4 BigQuery Export schema
  ```

  The label is the join key. Never use positional labels like `[^1]`, because agents reorder lists.

### `generated` and `verified` (§5.2)

```yaml
generated: { by: reference_agent/gemini-2.5-pro, at: "2026-06-20T22:53:05Z" }
verified:
  - { by: "human:ahormati", at: "2026-06-25T09:00:00Z" }
  - { by: "process:finance-nightly", at: "2026-06-26T02:00:00Z" }
```

- `generated` records how the current content was made. `generated.by` is REQUIRED in it.
- `generated.at` is the time of the last **meaningful** change. A trivial edit (format, whitespace,
  link repair) does not change it.
- `verified` is a list of events. Each event REQUIRES both `by` and `at`. Consumers ignore an event
  that lacks either.
- One verifier MAY be written as a bare `{ by, at }` mapping. Consumers treat it as a one-item list.

### Trust tiers (§5.3)

A verification event is **current** when its `at` is equal to or later than `generated.at`, or when
`generated` is absent. Consumers MUST calculate the tier only from current events. Earlier events
stay in the file as history ("verified before the last change").

- No current event: **unverified**.
- Current events from non-`human:` actors only: **machine-confirmed**.
- A current event from a `human:<id>` actor: **human-reviewed**.

When an agent rewrites a concept after a human review, the human has not read the new text. As a result, the
concept is not human-reviewed until a person confirms it again. Tiers are advisory, not access
control.

Example: this concept is machine-confirmed, because the human check predates the rewrite.

```yaml
generated: { by: reference_agent/gemini-2.5-pro, at: "2026-09-02T10:00:00Z" }
verified:
  - { by: "human:jsmith", at: "2026-08-25T09:00:00Z" }             # history
  - { by: "process:finance-nightly", at: "2026-09-03T02:00:00Z" }  # current
```

### `status` and `superseded_by` (§5.4)

```yaml
status: deprecated                     # draft | stable (the default) | deprecated
superseded_by: /metrics/gross-margin.md
```

- `draft`: not yet reviewed, possibly incomplete. `stable`: ready. `deprecated`: kept for links and
  history, not current.
- A value outside this list is **not** `stable`. Filters to current knowledge exclude the concept.
  Consumers SHOULD show the raw value.
- `superseded_by` is one path (§6.2) to the replacement. It has a meaning only with
  `status: deprecated`. Consumers that filter to current knowledge SHOULD follow it.
- **To move or rename a concept,** leave a short deprecated concept at the old path with
  `superseded_by` set to the new path. Old links and stored references keep working.

### `stale_after` (§5.5)

```yaml
stale_after: "2026-09-23T00:00:00Z"   # stale when now >= stale_after
```

- An absolute instant, not a TTL.
- Stale means "check again", not "false".
- Omit it when no review date is known. Do not invent one.
- Empty or null is the same as absent.
- A value that does not parse is never fresh. Consumers SHOULD show it as malformed.

## Links and paths (§6)

**One resolution rule** for link targets and path field values:

1. A value with a URI scheme (`https:`) is an absolute URL.
2. A value that starts with `/` resolves from the bundle root.
3. Any other value resolves from the **directory of the file that contains it**.

- Both in-bundle forms are valid, and the spec recommends neither. Consumers MUST resolve both.
- A value that resolves outside the bundle root is external. Consumers MUST NOT read it from the
  local file system.
- Targets are RFC 3986 URI references. Percent-encode spaces and reserved characters
  (`my%20concept.md`). Paths are case-sensitive. Do not make two paths that differ only by case.
- **Path fields:** `resource`, `sources[].resource`, `computation`, `executor.resource`,
  `attester.resource`, and `superseded_by`. In frontmatter, prefer the `/` form
  (`/references/attesters/sql-equality.py`); in body links, either form is fine.

### Links (§6.1)

- A link refers to a concept when its target, without a `#fragment`, resolves to a concept file. A
  link to an asset or directory is valid but is not a concept edge.
- Only `[text](target)` and reference-style links count. `[[wikilinks]]` are not OKF links.
- Consumers MUST accept broken links. A missing target can be knowledge nobody has written yet.

### The bundle graph (§6.4)

Two kinds of directed edges: a link from a concept to a concept, and a path field that resolves to a
concept (from the concept that holds the field to the target).

## `index.md` (§8)

A subdirectory `index.md` has **no** frontmatter. Its body is one or more sections, each a heading
over `* [Title](url) - description` entries:

```markdown
# Subdirectories

* [tables](tables/index.md) - BigQuery tables the bundle grounds against.

# Metric

* [Revenue](revenue.md) - Recognized revenue per the FY2026 policy.
```

Entries SHOULD use the linked concept's `description`. Producers MAY generate index files.
Consumers MAY synthesize one when it is missing.

### Bundle metadata (§8.1)

The bundle-root `index.md` MAY carry frontmatter with these optional keys, plus extension keys that
apply to the bundle:

```yaml
---
okf_version: "0.3"
title: Acme retail analytics
description: Tables, metrics, and sanctioned computations for Acme retail. Use it for sales and margin questions.
license: CC-BY-4.0
---
```

- `okf_version`: a quoted string.
- `title`: a display name for the bundle.
- `description`: one sentence on the bundle's scope **and when to use it**. An agent with many
  bundles reads it to pick one.
- `license`: an SPDX expression, or a path (§6.2) to a license file in the bundle.
- A producer that regenerates `index.md` MUST keep this frontmatter.
- Producers SHOULD put a bundle-root `index.md` with `okf_version` in every bundle.

## `log.md` (§9)

```markdown
# Update Log

## 2026-05-22
* **Update**: Added a BigQuery table reference for [Customer Metrics](tables/customer-metrics.md).
* **Creation**: Established the [Dataplex Playbook](playbooks/dataplex.md).

## 2026-05-15
* **Initialization**: Created foundational directory structure.
```

- Newest date first. Date headings MUST be `## YYYY-MM-DD`.
- The bold lead word is a convention, not a requirement.
- `log.md` has **no** frontmatter. It may sit at any level to record that scope's history.

## Attested Computation (§10)

A standalone concept with a sanctioned way to compute a value and the means to check a run.
Concepts that need the value (a `Metric`, a dashboard) link to it. Use one computation per concept,
so revenue, profit, and margin each verify, expire, and attest on their own. Group them in a
`computations/` directory, not in frontmatter.

````markdown
---
type: Attested Computation
title: Revenue for fiscal year
description: Recognized revenue for a fiscal year, per Finance's definition.
status: stable
runtime: bigquery                      # REQUIRED for this type; defines what parameters mean
parameters:                            # the only holes an agent may fill
  - { name: year, type: integer, required: true }   # name and type REQUIRED; required defaults to false
executor:
  resource: /references/skills/run-on-bq.md   # run instructions or code
  receipt: [job_id, executed_sql, result]     # evidence a run must return
attester:
  resource: /references/attesters/sql-equality.py   # deterministic, no-LLM verdict code
generated: { by: reference_agent/gemini-2.5-pro, at: "2026-06-20T14:00:00Z" }
verified: { by: "human:ahormati", at: "2026-06-25T09:00:00Z" }
stale_after: "2026-12-31T00:00:00Z"
sources:
  - id: rev-policy
    resource: https://wiki.acme/finance/revenue-recognition
    title: Revenue recognition policy
---

# Computation

```sql
SELECT SUM(amount) AS revenue
FROM finance.recognized_revenue
WHERE fiscal_year = @year
```

Recognized revenue per the recognition policy.[^rev-policy]

[^rev-policy]: Revenue recognition policy
````

- **Common parameter types:** `string`, `integer`, `number`, `boolean`, `date`, `timestamp`. Others
  are runtime-specific.
- **Where the computation is (§10.3):**
  1. If `computation` is set, it is the file at that path.
  2. Otherwise it is the first fenced code block in the section headed `Computation`, at any ATX
     level. The section ends at the next heading of the same or a higher level.
  3. If neither exists, the concept is **not attestable**.
  Put exactly one fenced block in the `Computation` section.
- Consumers MUST NOT show a value as attested when the concept has no `runtime` or no `attester`.
- The agent supplies parameter *values* only. It MUST NOT write or edit the computation. The
  attester rebinds the computation independently and compares it with the compiled artifact in the
  receipt (`executed_sql`, `compiled_sql`).
- **Consumer flow (informative, §10.5):** discover by a frontmatter scan for the type, load the
  contract and computation, bind parameters, execute, attest the receipt (the verdict is a mapping
  with a boolean `ok` and an optional `reason`), then gate. Do not show a value that failed
  attestation; show the failure instead of dropping it. Warn, or do not show the value, when
  `now >= stale_after`.
- `verified` confirms the *definition* (per document, stored in the bundle). Attestation confirms
  one *run* (per call, at runtime, never stored). OKF needs both.

## Actors (§7)

`generated.by`, `verified[].by`, and `sources[].author` use one convention:

| Form | Meaning | Example |
|---|---|---|
| `<producer>/<version>` | An agent or tool. | `reference_agent/gemini-2.5-pro`, `claude-code/claude-opus-5-5` |
| `human:<id>` | A person. | `human:ahormati` |
| `team:<id>` | A group of people. | `team:finance-fpa` |
| `process:<id>` | An automated process. | `process:finance-nightly` |

- Other schemes are allowed. Consumers treat them as non-human.
- Only `human:` gives the human-reviewed tier, so producers MUST use it for content a person wrote
  or confirmed.
- A `team:` verifier gives machine-confirmed, because a team name does not say who checked.
- Quote `<scheme>:<id>` values in flow mappings (`"human:ahormati"`), as the spec examples do.

## Conformance (§11)

A bundle is **conformant** with v0.3 when:

1. Every frontmatter block in a `.md` file under the bundle root parses as a YAML mapping.
2. `index.md` and `log.md` agree with §8 and §9 when present.

A `.md` file without frontmatter or `type` is not a concept and does not break conformance.

**Consumer rules (§11.2).** Consumers MUST resolve both in-bundle path forms, MUST NOT read paths
outside the bundle root, MUST NOT treat reserved files as concepts, MUST NOT reject unknown keys,
MUST NOT treat an unparseable `stale_after` as fresh, MUST NOT show a value as attested without
`runtime` and `attester`, MUST NOT reject a concept for a missing optional family, and MUST
calculate trust tiers from current events only.

**Absent, empty, and odd shapes:**

1. Null, an empty string, and an empty list mean the key is absent.
2. Where a field is a list (`tags`, `sources`, `verified`, `parameters`), one item counts as a
   one-item list. A scalar `tags` value is one tag; never split it at commas.
3. Consumers ignore a family entry that lacks its REQUIRED key, and SHOULD warn.
4. A value outside a defined vocabulary is kept; consumers MAY warn.

Consumers MUST NOT reject a bundle for missing optional fields, unknown `type` values, unknown keys,
broken links, or missing `index.md` files.

## Versioning (§12)

- Versions are `<major>.<minor>`. **Before 1.0**, a minor version MAY break things, and §13 lists
  each break with a fallback. **From 1.0**, minor versions only add.
- Declare the version with `okf_version` in the bundle-root `index.md`. A consumer that does not know
  the version SHOULD consume on a best-effort basis and SHOULD NOT refuse the bundle.
- **Fallbacks for v0.2-or-earlier bundles, or bundles with no version (§12.1):** a path field without
  a leading `/` that does not resolve from its file MAY resolve from the bundle root. The v0.1
  fallbacks also apply: a legacy `timestamp` stands in for `generated.at`, and a body `# Citations`
  list stands in for `sources`.
- **Deferred to a later version:** the runtime protocol (receipt and verdict wire formats), the
  attester ABI and sandboxing, attestation caches, semantic-layer templates (Looker, dbt), typed
  relationships, validity windows, source drift signals, and a `refuted` verification event. Use
  extension keys until then.

## Migrate a bundle from v0.2 to v0.3

v0.3 has two breaking changes (§13.1). Everything else is a clarification or an optional addition.

1. **Fix bare path fields.** v0.3 resolves `references/x.py` from the file's directory, not the
   bundle root. Prefix in-bundle path fields with `/` (`/references/x.py`). `okf.py validate` reports
   each one as W127 while the bundle still declares 0.2, and as W111 after you declare 0.3.
2. **Accept lower trust tiers.** Verification events older than `generated.at` no longer count.
   `okf.py validate` reports each concept whose tier dropped as W125. Do not edit `verified` or
   `generated.at` to restore a tier; a person or process must confirm the concept again. A
   date-only `verified.at` on the same day as `generated.at` also drops out, because it means
   midnight UTC.
3. **Clean up what is now stricter.** Quote `okf_version`. Remove frontmatter from `log.md` and from
   subdirectory `index.md` files. Give every `verified` event both `by` and `at`. Add a seconds field
   and an offset to any date-time timestamp.
4. **Use what is new, where it helps.** Add `title`, `description` (scope plus when to use the
   bundle), and `license` to the root `index.md`. Use `superseded_by` on deprecated concepts. Rename
   private keys to `x-<producer>-<name>`.
5. **Declare the version.** Set `okf_version: "0.3"` in the root `index.md`, then run
   `okf.py validate` again.
