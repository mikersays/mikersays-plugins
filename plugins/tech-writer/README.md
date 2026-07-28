# tech-writer

Two documentation rewriters in one plugin:

- **`/tech-writer`** — Google's Technical Writing One and Two guidelines, extended with clarity rules adapted from ASD-STE100 Issue 9. For READMEs, API docs, guides, and ordinary prose.
- **`/ste`** — strict Simplified Technical English (ASD-STE100 Issue 9). For safety-critical procedures, runbooks, maintenance manuals, and documents headed for translation.

## Usage

```
/tech-writer path/to/document.md   # review a specific file
/tech-writer                       # review the file currently in context

/ste path/to/runbook.md            # rewrite into Simplified Technical English
```

## What it does

1. Reads the target document
2. Applies every applicable rule
3. Rewrites the file in place
4. Reports a summary of changes grouped by rule category

## `/tech-writer` rules applied

- **Words & Terminology** — consistent terms, proper acronyms, clear pronouns
- **Noun phrases** — cap stacked modifiers at three words, hyphenate what binds
- **Active Voice** — convert passive to active, rewrite modal passives, never invent an actor
- **Clear Sentences** — strong verbs, no nominalizations, no "there is/are," measurable data over vague adjectives
- **Short Sentences** — one idea per sentence, no chained or dangling participles, complete subjects and verbs, keep the articles
- **Lists & Tables** — parallel structure, imperative verbs, one action per step, introductory sentences
- **Notes & Warnings** — notes carry background only; label the hazard, lead with the action, name the real consequence
- **Paragraphs** — strong openers, single topic, explicit transitions
- **Audience** — state the audience, avoid idioms and Latin abbreviations, explain jargon
- **Document Organization** — scope, prerequisites, key points first
- **Self-Editing** — second person, conditions before instructions, code font
- **Large Documents** — outlines, task-based headings, progressive disclosure
- **Sample Code** — correct, concise, descriptive names, comment the "why"
- **Illustrations** — captions first, limited density, callouts for focus

## `/ste` rules applied

The nine rule sections of ASD-STE100 Part 1, paraphrased with software-documentation examples:

1. **Words** — one word, one part of speech, one meaning; technical nouns and technical verbs by category
2. **Multi-word nouns** — three-word cap, first-mention expansion, hyphenation
3. **Verbs** — six verb forms only, no perfect tenses, no progressives, no `-ing` outside a small set, active voice
4. **Sentences** — complete subjects and verbs, no contractions, strict vertical-list mechanics, article rules
5. **Procedural writing** — 20-word cap, one instruction per step, condition first, notes carry no instructions
6. **Descriptive writing** — no imperatives, 25-word cap, repeat key terms, six sentences per paragraph
7. **Safety instructions** — two severity levels, grade to the worst case, action first, consequence after
8. **Punctuation and word count** — no semicolons, hyphen and parenthesis rules, how to count a sentence
9. **Writing practices** — rebuild rather than force a substitution, no phrasal verbs, no Latin abbreviations

`/ste` also ships `skills/ste/substitutions.md`, a curated table of 122 common unapproved words and their approved replacements, selected for words that actually appear in software documentation.

### The two skills disagree on purpose

STE and Google's guidelines are different standards. They conflict on sentence length caps, `-ing` forms, nouns used as verbs, gerund vs. imperative headings, `we` vs. `you`, contractions, list punctuation, phrasal verbs, imperatives in prose, and severity labels. Pick one per document. Never run both over the same file, and never "fix" `/ste` output with `/tech-writer`. `/ste` documents the full list of divergences.

## Subagents

The plugin registers two Task agents that Claude can spawn autonomously to review docs in the background:

```
Task(subagent_type="tech-writer", prompt="Review plugins/ship/README.md")
Task(subagent_type="ste", prompt="Convert docs/runbooks/failover.md to STE")
```

Both use Sonnet for fast, cost-effective reviews and have access to Read, Write, Edit, Glob, and Grep tools.

## Sources

- Google Technical Writing One and Technical Writing Two.
- **ASD-STE100 Simplified Technical English, Issue 9** (January 2025), © ASD, published by the AeroSpace, Security and Defence Industries Association of Europe.

Rules from ASD-STE100 are paraphrased with our own examples, and rule numbers are kept as citation anchors. Only the bare numbers (1.1, 4.3, 8.6) are ASD's; the letter suffixes used in `/ste` are this plugin's own subdivision of a single ASD rule. This plugin does not reproduce the standard's text or the full ASD-STE100 dictionary; `skills/ste/substitutions.md` reproduces 122 not-approved-word entries with their ASD-assigned alternatives. This plugin is not affiliated with, endorsed by, or approved by ASD. For authoritative use, obtain ASD-STE100 from ASD.

## Installation

```bash
/plugin install tech-writer@mikersays-plugins
```
