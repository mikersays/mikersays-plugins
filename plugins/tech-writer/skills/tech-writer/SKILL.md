---
name: tech-writer
description: Review and rewrite documentation in place — Google's Technical Writing guidelines for READMEs, guides, and ordinary prose, or strict Simplified Technical English (ASD-STE100) for safety-critical procedures, runbooks, and translation-bound docs. The standard is chosen automatically from the document, or by explicit request ("use STE", "Simplified Technical English", "Google style"). Use when asked to polish, edit, clean up, review, or improve the clarity of a README, doc, or markdown file, or when asked for STE / controlled language.
argument-hint: "[file path] [ste|google]"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Tech Writer

Review and rewrite documentation using one of two standards: Google's Technical Writing One and Two guidelines, or strict Simplified Technical English (ASD-STE100 Issue 9). They are different, sometimes contradictory standards — this skill picks exactly one per document and never blends them.

## Process

1. **Pick the target file.** Use `$ARGUMENTS` if provided; if that path does not exist on disk, run Glob for similar filenames and ask the user to confirm before editing anything. Otherwise use the file currently in context. If neither exists, ask.
2. **Choose the standard** (see below).
3. **Read the whole file** before editing — context matters for terminology, pronouns, and classification.
4. **Read only the matching rule file** — `rules-google.md` or `rules-ste.md` in this skill's directory — and follow its Process, Boundaries, and Output format exactly. Do not read the other rule file and do not apply any of its rules.
5. **Report** using that rule file's output format, and state up front which standard you applied and why.

## Choose the standard

**1. An explicit request always wins.** Check `$ARGUMENTS` and the surrounding request for a direct mention of a standard before you look at the document itself:

- → **STE**: `ste`, `STE`, `Simplified Technical English`, `ASD-STE100`, `controlled language`, "for translation," "for non-native readers."
- → **Google**: `google`, `Google style`, `Google technical writing`, `tech-writer-google` (an old command name).

**2. Otherwise, classify the document.** Read enough of it to tell:

- → **STE** — safety-critical procedures, runbooks, incident playbooks, installation and maintenance manuals, or anything the request says is headed for translation or for readers with limited English.
- → **Google** (the default) — READMEs, API docs, conceptual guides, marketing pages, changelogs, blog posts, and ordinary prose.

**3. If it's genuinely ambiguous** — for example a runbook written in a conversational register, or a doc that mixes procedure and narrative — ask the user to pick, in one short question naming both options and the one-line reason each applies. Don't guess on a real toss-up; guessing risks silently applying the wrong of two contradictory standards.

### Why this matters: the standards actively disagree

| Subject | STE | Google |
|---|---|---|
| Nouns used as verbs | Banned. `Do a test of the response.` | Fine — strong specific verbs are preferred |
| Sentence length | Hard cap: 20 words procedural, 25 descriptive | Semantic test only: one idea per sentence |
| `-ing` forms | Banned outside a small approved set and technical nouns | Restricted only in chained participial phrases; otherwise allowed |
| Procedure headings | Gerund headings permitted: `## Packaging` | Reader's task: `## Package the release` |
| First person | `we` allowed where the organization is the actor | Use `you`, not `we` |
| Contractions | Expanded in full | Left alone |
| List punctuation | Terminal period after the last fragment | Strictly parallel punctuation across items |
| Phrasal verbs | Replaced with single verbs | Kept — `log in`, `roll back`, `spin up` |
| Imperatives in prose | Banned outside procedures | Fine where it reads naturally |
| Severity labels | `WARNING` and `CAUTION` by convention | Note and Warning callouts; no fixed severity vocabulary |

Never "fix" one standard's output with the other, and never run both rule files over the same file.

## Shared boundaries

These apply regardless of which standard you picked — the per-standard rule file adds more of its own:

- Don't change technical meaning. If something reads as factually wrong, flag it instead of silently fixing it.
- Don't add sections, features, or claims the author didn't write.
- Don't delete information — reword or relocate it.
- Never alter quoted text, UI strings, command names, or flag spellings.
- If the document is already well-written for its standard, say so and stop. Don't churn for the sake of churn.

## Word substitutions (STE only)

When applying STE, `substitutions.md` in this skill's directory has a curated table of common unapproved words and their approved replacements. Consult it whenever you need a replacement.

## Source and attribution

`rules-google.md`'s clarity rules and all of `rules-ste.md` are paraphrased from **ASD-STE100 Issue 9** (January 2025), © ASD, published by the AeroSpace, Security and Defence Industries Association of Europe. This plugin is not affiliated with, endorsed by, or approved by ASD, does not reproduce the standard's text, and does not contain the full ASD-STE100 dictionary. For authoritative use, obtain ASD-STE100 from ASD.
