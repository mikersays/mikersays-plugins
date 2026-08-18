# tech-writer

One documentation rewriter, two standards. `/tech-writer` reads the document, picks the standard that fits it, and applies exactly that one:

- **Google's Technical Writing One and Two** guidelines, extended with clarity rules adapted from ASD-STE100 Issue 9. The default — for READMEs, API docs, guides, and ordinary prose.
- **Simplified Technical English** (ASD-STE100 Issue 9), strict. For safety-critical procedures, runbooks, maintenance manuals, and documents headed for translation.

## Usage

```
/tech-writer path/to/document.md        # pick the standard automatically
/tech-writer                            # review the file currently in context

/tech-writer path/to/runbook.md ste     # force Simplified Technical English
/tech-writer path/to/README.md google   # force Google's guidelines
```

An explicit request always wins — `ste`, `Simplified Technical English`, `ASD-STE100`, `controlled language`, "for translation," or `google` and `Google style` in the arguments or the surrounding request. Otherwise the skill classifies the document: procedures, runbooks, incident playbooks, and installation or maintenance manuals go to STE; everything else goes to Google. On a genuine toss-up — a runbook in a conversational register, a doc that mixes procedure and narrative — it asks you rather than guessing.

## What it does

1. Picks the standard, and states which one and why
2. Reads the target document in full
3. Reads only the matching rule file, then applies every applicable rule
4. Rewrites the file in place
5. Normalizes British spellings to US English with the bundled converter
6. Reports a summary of changes in that standard's output format

## Layout

```
skills/tech-writer/SKILL.md                  ← router: picks the standard, shared boundaries
skills/tech-writer/rules-google.md           ← Google Technical Writing rules, with examples
skills/tech-writer/rules-ste.md              ← the nine ASD-STE100 rule sections, with examples
skills/tech-writer/substitutions.md          ← 122 unapproved words and their approved replacements
skills/tech-writer/scripts/en_gb_to_en_us.py ← en-GB → en-US spelling converter (stdlib Python 3.9+)
agents/tech-writer.md                        ← background subagent, both standards inlined
```

Only one rule file is ever loaded per document. The two are never run over the same file.

## Google rules applied

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

## STE rules applied

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

`skills/tech-writer/substitutions.md` holds a curated table of 122 common unapproved words and their approved replacements, selected for words that actually appear in software documentation.

### The two standards disagree on purpose

STE and Google's guidelines conflict on sentence length caps, `-ing` forms, nouns used as verbs, gerund vs. imperative headings, `we` vs. `you`, contractions, list punctuation, phrasal verbs, imperatives in prose, and severity labels. The skill picks one per document and never blends them, never "fixes" one standard's output with the other, and never runs both rule files over the same file. `SKILL.md` tabulates the full list of divergences.

## Dialect pass

Both standards want US spelling — `rules-ste.md` rule 1.14 says so outright, and Google's guidelines are US English — so the skill runs a bundled converter over the rewritten file. It is stdlib-only Python 3.9+ and runs standalone from any repo:

```bash
python3 plugins/tech-writer/skills/tech-writer/scripts/en_gb_to_en_us.py --check docs/api.md
python3 plugins/tech-writer/skills/tech-writer/scripts/en_gb_to_en_us.py --write docs/api.md
```

`--check` reports and never writes, exiting 1 when it finds anything:

```
docs/api.md:1:3: Colour -> Color  (rule: our-or)
docs/api.md:3:14: normalises -> normalizes  (rule: ise-ize)
docs/api.md:8:45: licence -> license  (rule: ce-se)
```

`--write` applies them and prints `docs/api.md: 9 change(s) applied, 0 flagged`. Also available: `--diff` for a unified diff, `--stdin` to filter stdin to stdout, `--json` and `--stats` to reshape the report, and `--selftest` to run the built-in assertions.

**What it does not touch.** Fenced and indented code blocks, inline code spans, link and image targets, HTML tags, frontmatter identifiers, and anything shaped like an identifier — the flag `--colour-output` and the symbol `ColourMap` survive intact. Words with two live meanings (`disc`, `draughts`, `storeyed`) and proper nouns (`the Labour Party`) are reported under a separate `-- flagged, not applied without --aggressive --` heading and are never written; the skill surfaces those to you instead of guessing. The pass is mechanical, so the skill still reads the result and reverts anything that landed in a quoted UI string or a citation.

## Subagent

The plugin registers one Task agent that Claude can spawn autonomously to review docs in the background. It carries both standards and the same routing rule:

```
Task(subagent_type="tech-writer", prompt="Review plugins/ship/README.md")
Task(subagent_type="tech-writer", prompt="Convert docs/runbooks/failover.md to STE")
```

It uses Sonnet for fast, cost-effective reviews and has access to Read, Write, Edit, Glob, Grep, and Bash.

## Sources

- Google Technical Writing One and Technical Writing Two.
- **ASD-STE100 Simplified Technical English, Issue 9** (January 2025), © ASD, published by the AeroSpace, Security and Defence Industries Association of Europe.

Rules from ASD-STE100 are paraphrased with our own examples, and rule numbers are kept as citation anchors. Only the bare numbers (1.1, 4.3, 8.6) are ASD's; the letter suffixes used in `rules-ste.md` are this plugin's own subdivision of a single ASD rule. This plugin does not reproduce the standard's text or the full ASD-STE100 dictionary; `skills/tech-writer/substitutions.md` reproduces 122 not-approved-word entries with their ASD-assigned alternatives. This plugin is not affiliated with, endorsed by, or approved by ASD. For authoritative use, obtain ASD-STE100 from ASD.

## Installation

```bash
/plugin install tech-writer@mikersays-plugins
```
