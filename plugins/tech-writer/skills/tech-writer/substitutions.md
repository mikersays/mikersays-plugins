# STE word substitutions

A curated table of common unapproved words and their approved STE replacements, selected for words that actually appear in software and technical documentation. Use it with `/tech-writer` when it applies the Simplified Technical English standard.

**This is not the ASD-STE100 dictionary.** The standard approves roughly 875 words and lists about 1,274 unapproved ones. This table is a selection of ASD's not-approved-word entries and their ASD-assigned alternatives, narrowed to the entries that matter for the kind of documents this plugin sees. It is a starting point, not an authority: a word missing from this table is not thereby approved, and the plugin cannot verify approval status. For authoritative work, obtain ASD-STE100 Issue 9 from ASD.

## How to use it

STE fixes one meaning and one part of speech to each approved word (rules 1.2 and 1.3). So a substitution is often not a word-for-word swap:

- Where the replacement keeps the part of speech, swap it in: `utilize` becomes `use`.
- Where it changes part of speech, rebuild the sentence around the replacement (rule 1.2a): `has the ability to retry` becomes `can retry`, not `has the can to retry`.
- Where no replacement fits without damaging the meaning, rebuild the sentence from what the reader must actually do (rule 9.1a).
- Never apply a substitution inside quoted text, a UI label, a command, or a flag name (rule 1.14a). `--verify-checksum` stays `--verify-checksum`.

Notes in the third column mark the entries where a blind swap goes wrong.

## Verbs

| Avoid | Use | Note |
|---|---|---|
| `utilize` | `use` |  |
| `employ` | `use` |  |
| `obtain` | `get` |  |
| `acquire` | `get` |  |
| `achieve` | `get` |  |
| `accomplish` | `do, complete` |  |
| `perform` | `do` |  |
| `conduct` | `do` |  |
| `carry out` | `do` |  |
| `undertake` | `do, start` |  |
| `execute` | `do` | Swap in prose ("execute the procedure" → "do the procedure"). Keep "execute" where it is the literal action on code, a query, or a binary. |
| `commence` | `start` |  |
| `initiate` | `start` |  |
| `begin` | `start` |  |
| `actuate` | `start, operate` |  |
| `terminate` | `stop` |  |
| `cease` | `stop` |  |
| `halt` | `stop` |  |
| `discontinue` | `stop` |  |
| `eliminate` | `remove` |  |
| `facilitate` | `help` |  |
| `assist` | `help` |  |
| `ensure` | `make sure` |  |
| `verify` | `make sure` |  |
| `confirm` | `make sure` |  |
| `ascertain` | `make sure` |  |
| `provide` | `give, supply` |  |
| `retain` | `keep` |  |
| `maintain` | `keep` | Only in the "keep" sense ("maintain the connection" → "keep the connection"). Leave it alone when it means maintaining software. |
| `proceed` | `continue` |  |
| `determine` | `find` |  |
| `locate` | `find` |  |
| `evaluate` | `examine` |  |
| `modify` | `change` |  |
| `alter` | `change` |  |
| `amend` | `change` |  |
| `substitute` | `replace` |  |
| `incorporate` | `include` |  |
| `comprise` | `have, contain` |  |
| `consist of` | `have` |  |
| `accumulate` | `collect` |  |
| `indicate` | `show` |  |
| `display` | `show` |  |
| `inform` | `tell` |  |
| `notify` | `tell` |  |
| `advise` | `tell, recommend` | "tell" when passing on information, "recommend" when suggesting a course of action — pick by sense. |
| `consult` | `refer` | Takes a preposition: "consult the API docs" → "refer to the API docs". |
| `observe` | `see, monitor` | "see" for a one-off observation, "monitor" for watching something over time. |
| `prohibit` | `prevent` |  |
| `hinder` | `prevent` |  |
| `allow` | `let` |  |
| `permit` | `let` |  |
| `enable` | `let` | Only where it means "allow" ("enables you to" → "lets you"). Keep "enable" for switching a flag, feature, or service on. |
| `attempt` | `try` |  |
| `augment` | `increase` |  |
| `produce` | `make, cause` |  |
| `dispose of` | `discard` |  |
| `may` | `can` | "can" for ability or permission; for uncertainty, recast with "possibly" so permission and possibility never blur. |
| `shall` | `must` |  |
| `should` | `must` | STE recasts to "must" or to an if-clause. Keep "should" only where RFC 2119 keyword semantics are deliberate. |

## Nouns

| Avoid | Use | Note |
|---|---|---|
| `ability` | `can` | Noun becomes a verb, so recast: "has the ability to retry" → "can retry". |
| `proximity` | `near` | "in close proximity to the cache" → "near the cache". |
| `comparison` | `compare` | Nominalization: "make a comparison of A and B" → "compare A and B". |
| `completion` | `end, complete` | "on completion of the build" → "when the build ends". |
| `preparation` | `prepare` | "in preparation for the upgrade" → "to prepare for the upgrade". |
| `limitation` | `limit` |  |
| `technique` | `method` |  |
| `activity` | `task, work` |  |
| `portion` | `part` |  |
| `discrepancy` | `difference` |  |
| `transition` | `change` |  |
| `event` | `if` | Kills the whole wordy phrase: "in the event of a timeout" / "in the event that it times out" → "if it times out". |
| `duration` | `during` | "for the duration of the migration" → "during the migration". |
| `reason` | `cause, because of` | "for this reason" → "because of this"; "the reason is that" → "because". |
| `consequence` | `because of` | "as a consequence of the outage" → "because of the outage". |

## Adjectives

| Avoid | Use | Note |
|---|---|---|
| `additional` | `more` |  |
| `further` | `more` |  |
| `several` | `some` |  |
| `various` | `different` |  |
| `considerable` | `large, important` |  |
| `significant` | `important` |  |
| `potential` | `possible` |  |
| `feasible` | `possible` |  |
| `prescribed` | `specified` |  |
| `permissible` | `permitted` |  |
| `inadvertent` | `accidental` |  |
| `abnormal` | `unusual, incorrect` |  |
| `adverse` | `bad` |  |
| `hazardous` | `dangerous` |  |
| `conventional` | `standard` |  |
| `identical` | `same` |  |
| `principal` | `primary` |  |
| `proper` | `correct` |  |
| `associated` | `related` |  |
| `respective` | `related` | Usually deletable: "each service and its respective config" → "each service and its config". |
| `pertinent` | `applicable` |  |
| `desired` | `necessary, correct` |  |
| `following` | `these` | "the following steps" → "these steps"; drop it entirely when a colon already introduces the list. |
| `capable` | `can` | Adjective becomes a verb, so recast: "is capable of caching results" → "can cache results". |
| `unable` | `cannot` | Recast: "is unable to connect" → "cannot connect". |

## Adverbs

| Avoid | Use | Note |
|---|---|---|
| `properly` | `correctly` |  |
| `extremely` | `very` |  |
| `highly` | `very` |  |
| `completely` | `fully` |  |
| `thoroughly` | `fully` |  |
| `generally` | `usually` |  |
| `normally` | `usually` |  |
| `however` | `but` | Changes part of speech, so join the clauses: "X. However, Y." → "X, but Y." |

## Prepositions

| Avoid | Use | Note |
|---|---|---|
| `prior to` | `before` |  |
| `due to` | `because of` |  |
| `by means of` | `with` |  |
| `as to` | `about` |  |
| `via` | `through` |  |
| `within` | `in` |  |
| `excluding` | `without` |  |
| `beneath` | `below` |  |
| `upon` | `on, when` |  |

## Conjunctions

| Avoid | Use | Note |
|---|---|---|
| `whilst` | `while` |  |
| `till` | `until` |  |
| `whenever` | `when` |  |
| `once` | `when` | Only the conjunction: "once the server starts" → "when the server starts". Keep "once" meaning one time. |
| `as` | `because, while` | Ambiguous between cause and time — pick "because" or "while" to say which you mean. |

## Approved verbs

STE approves about 875 words in total, of which roughly 200 are verbs. That list is small on purpose: one verb per action, one meaning per verb, so a reader never has to choose between senses. When you need a verb and the natural one is not approved, the usual repair is an approved verb plus a technical noun — `do a test of`, `block the port with the firewall` — rather than a closer synonym.

The full approved-word list is part of ASD-STE100 and is not reproduced here.

---

Substitutions derived from **ASD-STE100 Simplified Technical English, Issue 9** (January 2025), © ASD. This plugin is not affiliated with or endorsed by ASD.
