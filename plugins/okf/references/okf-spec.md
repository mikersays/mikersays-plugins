# Open Knowledge Format v0.2 — working reference

Condensed from the normative spec at
<https://github.com/GoogleCloudPlatform/open-knowledge-format/blob/main/SPEC.md>.
Section numbers (§) refer to that document. Read the full spec when something here is ambiguous.

OKF represents *knowledge* (the metadata, context, and curated insight around data and systems) as a
directory of markdown files with YAML frontmatter. No schema registry, no central authority, no
required tooling. Anyone can produce it (humans, agents, export pipelines); anyone can consume it
(an LLM loading files, a static site, a search index, a graph viewer).

## Vocabulary (§2)

| Term | Meaning |
|---|---|
| **Bundle** | A self-contained directory tree of knowledge documents. The unit of distribution (git repo, tarball, or subdirectory of a larger repo). |
| **Concept** | One markdown document = one unit of knowledge. A table, an API, a metric, a playbook, a policy, a computation. |
| **Concept ID** | The file path within the bundle, `.md` stripped: `tables/orders`. |
| **Link** | A normal markdown link between concepts. Expresses a relationship; the prose says which kind. |
| **Source** | Material a concept derives from, recorded in `sources`. |
| **Actor** | Who did something: `<producer>/<version>` for agents, `human:<id>` for people, `process:<id>` for automation (§7). |
| **Trust tier** | Derived from `verified`: unverified → machine-confirmed → human-reviewed (§5.3). |
| **Attested Computation** | A concept carrying a sanctioned way to compute a value plus the means to check a run of it (§10). |

## Bundle layout (§3)

```
bundle/
  index.md            # optional; directory listing (progressive disclosure)
  log.md              # optional; dated change history, newest first
  <concept>.md
  <group>/            # any grouping the producer likes: tables/, metrics/, playbooks/, computations/ …
    index.md
    <concept>.md
    <subgroup>/…
```

- `index.md` and `log.md` are **reserved** at every level and are never concepts.
- Directory structure is a producer choice. Common groupings: by concept type (`tables/`, `metrics/`),
  by system, or by domain. A `references/` directory conventionally holds mirrored external
  material, run instructions, and attester/executor code (§6.3).
- Tags live in frontmatter (`tags`); there is no tag file format.

## Concept document (§4)

```markdown
---
type: <Type name>                      # REQUIRED, the only always-required key
title: <display name>                  # recommended; consumers may derive from filename
description: <one sentence>            # recommended; index.md entries, previews, search snippets use it
resource: <canonical URI of the asset> # only for concepts bound to a physical asset
tags: [a, b]                           # optional
# provenance / trust / lifecycle families (below), computation fields (§10), any extra keys
---

<markdown body>
```

- `type` is free-form and uncontrolled: `BigQuery Table`, `API Endpoint`, `Metric`, `Playbook`,
  `Policy`, `Reference`, `Skill`, `Attested Computation`, … Pick descriptive, self-explanatory values.
  Consumers must tolerate unknown types.
- Extra frontmatter keys are allowed and must be preserved by consumers.
- Body: standard markdown. Favor structure (headings, lists, tables, fenced code) over prose.
  No required sections. Conventional headings: `# Schema` (columns/fields), `# Examples`
  (fenced code), `# Computation` (Attested Computation only).
- Legacy v0.1 forms: `timestamp:` (now `generated.at`) and a body `# Citations` list (now `sources`).

## Provenance, trust, lifecycle (§5)

All optional. Every timestamp is ISO 8601 **with an explicit UTC offset**: `2026-06-30T14:00:00Z`.

### `sources` (§5.1)

```yaml
sources:
  - id: ga4-schema                     # stable key; needed when the body cites this source
    resource: https://…/export-schema  # REQUIRED per entry: URL, bundle path, or a scope descriptor
    title: GA4 BigQuery Export schema
    author: team:ga4-docs              # actor convention; authority signal
    usage_count: 5000                  # exercises of the resource over usage_window; liveness signal
    last_modified: 2026-05-30T00:00:00Z  # when the SOURCE changed (≠ generated.at)
usage_window: { from: 2026-06-01T00:00:00Z, to: 2026-06-30T00:00:00Z }   # frames every usage_count
```

- `resource` may be a concrete artifact (URL, bundle-relative path, `references/…`) or a population
  descriptor like `all queries in BigQuery project X`.
- Credibility is **inferred from signals, never stored as a score**.
- Lineage is expressed through links: a `resource` pointing at another concept is already an edge.
- **Per-claim attribution** uses markdown footnotes whose label is a `sources[].id`:

  ```markdown
  The `events_` table is sharded daily as `events_YYYYMMDD`.[^ga4-schema]

  [^ga4-schema]: GA4 BigQuery Export schema
  ```
  The label is the join key. Never use positional labels like `[^1]`; agents reorder lists.

### `generated` and `verified` (§5.2)

```yaml
generated: { by: reference_agent/gemini-2.5-pro, at: 2026-06-20T22:53:05Z }  # who wrote it, last meaningful change
verified:                                                                     # who CONFIRMED it against sources/resource
  - { by: human:ahormati, at: 2026-06-25T09:00:00Z }
  - { by: process:finance-nightly, at: 2026-06-26T02:00:00Z }
```

- `generated.by` is required within `generated`. Writing and confirming are distinct.
- `verified` may be a bare mapping; consumers treat it as a one-element list. Latest `at` = "how recently".
- **Trust tier** (§5.3): no `verified` → *unverified*; only non-`human:` verifiers → *machine-confirmed*;
  any `human:<id>` verifier → *human-reviewed*. Advisory, not access control.

### `status` and `stale_after` (§5.4, §5.5)

```yaml
status: stable                       # draft | stable (default) | deprecated
stale_after: 2026-09-23T00:00:00Z    # absolute instant; stale when now >= stale_after
```

`deprecated` concepts are kept for links and history. `stale_after` is an instant, not a TTL.

## Actor convention (§7)

- `<producer>/<version>` — agents and tools: `reference_agent/gemini-2.5-pro`, `claude-code/claude-fable-5-1`
- `human:<id>` — a person: `human:ahormati`
- `process:<id>` — automation: `process:finance-nightly`

Trust classification keys off the `human:` prefix, so hand-authored or human-confirmed content
**must** use it. `team:<id>` appears in the wild for `sources[].author`.

## Links and paths (§6)

- Bundle-relative links begin with `/` and are the **recommended** form: `[customers](/tables/customers.md)`.
  Relative links (`./other.md`, `../computations/revenue.md`) also work.
- A link asserts an untyped relationship; the prose says which kind. Broken links are tolerated
  (they may be not-yet-written knowledge).
- Path-valued fields (`resource`, `sources[].resource`, `computation`, `executor.resource`,
  `attester.resource`) accept an absolute URL, a `/`-prefixed bundle path, or a relative path.

## `index.md` (§8)

No frontmatter, except a bundle-root `index.md` may carry `okf_version: "0.2"` (§12). One or more
sections, each a heading over a bullet list of `[Title](url) - description`:

```markdown
---
okf_version: "0.2"
---

# Subdirectories

* [tables](tables/index.md) - BigQuery tables the bundle grounds against.

# Metric

* [Revenue](revenue.md) - Recognized revenue per the FY2026 policy.
```

Descriptions should come from the linked concept's `description`. Producers may generate index
files; consumers may synthesize one when it is missing.

## `log.md` (§9)

Newest first, `## YYYY-MM-DD` date headings, bullet entries with a conventional bold lead word:

```markdown
# Update Log

## 2026-05-22
* **Update**: Added a BigQuery table reference for [Customer Metrics](/tables/customer-metrics.md).
* **Creation**: Established the [Dataplex Playbook](/playbooks/dataplex.md).

## 2026-05-15
* **Initialization**: Created foundational directory structure.
```

A `log.md` may sit at any level to record that scope's history.

## Attested Computation (§10)

A standalone concept that carries a sanctioned way to compute a value and the means to check a run.
Concepts that need the value (a `Metric`, a dashboard) link to it. One computation per concept:
revenue, profit, and margin each verify, expire, and attest independently.

```markdown
---
type: Attested Computation
title: Revenue for fiscal year
description: Recognized revenue for a fiscal year, per Finance's definition.
status: stable
runtime: bigquery                      # REQUIRED for this type; defines what parameters mean
parameters:                            # the only holes an agent may fill
  - { name: year, type: integer, required: true }
computation: references/lib/revenue.sql   # optional; instead of an inline fence
executor:
  resource: references/skills/run-on-bq.md   # run instructions or code
  receipt: [job_id, executed_sql, result]    # evidence a run must return
attester:
  resource: references/attesters/revenue.py  # deterministic, no-LLM verdict code, run consumer-side
generated: { by: reference_agent/gemini-2.5-pro, at: 2026-06-20T22:53:05Z }
verified: { by: human:ahormati, at: 2026-06-25T09:00:00Z }
stale_after: 2026-09-23T00:00:00Z
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

Binds only the declared `parameters`, per the recognition policy.[^rev-policy]

[^rev-policy]: Revenue recognition policy
```

- The computation is **either** an inline fence under `# Computation` **or** the file at `computation`.
- The agent supplies parameter *values* only; it never authors or edits the computation.
- `verified` confirms the *definition* (doc-level, stored). Attestation confirms a single *run*
  (per-call, runtime, never stored in the bundle). Both are needed.
- Consumer flow (informative): discover by type → load contract → bind parameters → execute via
  executor → attest the receipt → gate: refuse to display a failing attestation, warn or refuse
  when stale, surface the verdict on success.

## Conformance (§11)

A bundle is conformant when:

1. every non-reserved `.md` file has a parseable YAML frontmatter block,
2. every frontmatter block has a non-empty `type`,
3. `index.md` and `log.md` follow §8 and §9 when present.

Consumers must not reject a bundle for missing optional fields, unknown types, unknown keys,
broken links, or missing `index.md`. Everything beyond the three rules is SHOULD-level guidance.

## Versioning (§12)

`okf_version: "0.2"` in the bundle-root `index.md` frontmatter declares the target version.
Minor bumps are additive; major bumps may break. Consumers should attempt best-effort consumption
of versions they do not understand.
