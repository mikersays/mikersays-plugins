---
name: tech-writer
description: Review and rewrite documentation using Google's Technical Writing guidelines
argument-hint: "[file path]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Tech Writer — Review and Rewrite Documentation

Apply the conventions and guidelines from Google's Technical Writing One and Technical Writing Two courses to review and improve technical documentation.

## Process

1. **Determine the target file.**
   - If the user provided a file path via `$ARGUMENTS`, read that file.
   - If no argument was provided, identify the file currently in context (most recently discussed or open). If no file is apparent, ask the user which file to review.

2. **Read the file** in its entirety.

3. **Analyze the document** against every rule below. Track each change you make.

4. **Rewrite the file in place**, applying all applicable rules. Preserve the author's intent, meaning, and technical accuracy. Do not add new technical content or remove information — only improve how existing content is expressed and organized.

5. **Report a summary** of changes made, grouped by rule category (e.g., "Active Voice: converted 4 passive sentences," "Short Sentences: split 3 long sentences").

---

## Rules

Apply these rules in order. Every rule is mandatory when applicable.

### Words and Terminology

- **Define new or unfamiliar terms** where they first appear, or link to an existing definition. If the document introduces many terms, collect them in a glossary.
- **Use one term consistently** for each concept throughout the document. Never rename a concept midway.
- **Acronyms:** On first use, spell out the full term followed by the acronym in parentheses, both in bold — e.g., **Transmission Control Protocol** (**TCP**). After that, use only the acronym. Only create an acronym if it is significantly shorter than the full term AND appears many times. If used only a few times, spell it out every time.
- **Pronouns:** Place pronouns within five words of their referent noun. If a second noun intervenes, repeat the original noun instead. Replace ambiguous uses of *it*, *they*, *them*, *their*, *this*, and *that* with the specific noun. Place a noun immediately after *this* or *that* when used as a determiner (e.g., "this variable" not just "this").

### Active Voice

- **Prefer active voice** (actor + verb + target) over passive voice (target + verb + actor).
- Convert passive constructions to active. If the actor is missing from a passive sentence, determine who performs the action and name them.
- Imperative sentences (commands) are already active voice.

### Clear Sentences

- **Replace weak verbs** — forms of *be* (is, are, was, were), *occur*, *happen* — with strong, specific verbs. Example: "The error occurs when..." → "Dividing by zero raises the error..."
- **Eliminate "There is" and "There are"** constructions. Move the real subject to the front. Example: "There is a variable called `count` that stores..." → "The `count` variable stores..."
- **Replace vague adjectives and adverbs** with objective, measurable data. Example: "significantly faster" → "225–250% faster."

### Short Sentences

- **One idea per sentence.** If a sentence contains two thoughts, split it into two sentences.
- **Convert embedded lists into actual lists.** When a sentence uses "or" or "and" to chain three or more items, extract them into a bulleted or numbered list.
- **Remove filler words and phrases:**
  - "at this point in time" → "now"
  - "is able to" → "can"
  - "causes the triggering of" → "triggers"
  - "provides a detailed description of" → "describes"
  - "in order to" → "to"
- **Subordinate clauses:** If a subordinate clause (starting with *which*, *that*, *because*, *whose*, *until*, *unless*, *since*) branches away from the main idea, break it into its own sentence.
- **That vs. which (US English):** Use *that* for essential (restrictive) clauses without a comma. Use *which* for nonessential (nonrestrictive) clauses, preceded by a comma.

### Lists and Tables

- **Bulleted lists** for unordered items. **Numbered lists** for sequential steps or ranked items.
- **Parallel structure:** All items in a list must share the same grammatical form, capitalization, and punctuation.
- **Numbered list items** start with an imperative verb (e.g., "Download the package," "Configure the server").
- **Introduce every list and table** with a contextual sentence ending in a colon, ideally using the word "following."
- **Table cells:** Limit content to two sentences. Label every column with a meaningful header.

### Paragraphs

- **Opening sentence** must state the paragraph's central point. Busy readers may read only this sentence.
- **One topic per paragraph.** Remove or relocate sentences that don't belong.
- **Length:** Aim for 3–5 sentences. Avoid walls of text (7+ sentences) and excessive one-sentence paragraphs.
- **Each paragraph should answer** what you're telling the reader, why it matters, and how to use it.

### Audience

- **State the target audience** near the top of the document.
- **Avoid idioms** ("Bob's your uncle," "hit the ground running") and cultural references. Use plain, direct language.
- **Explain jargon and abbreviations.** Account for the curse of knowledge — terms obvious to the author may be opaque to the reader.

### Document Organization

- **State scope explicitly:** What the document covers and what it does not cover.
- **State prerequisites:** What the reader must know or have installed before reading.
- **Lead with key points.** Invest heavily in the opening section — readers decide within the first paragraph whether to continue.
- **Remove tangential content** that falls outside the stated scope, even if it's interesting.

### Self-Editing (Technical Writing Two)

- **Use second person** ("you") instead of first-person plural ("we").
- **Place conditions before instructions.** Example: "If the build fails, run `make clean`" — not "Run `make clean` if the build fails."
- **Format code-related text** — file names, variable names, commands, class names — in code font (backticks in Markdown).

### Large Documents (Technical Writing Two)

- **Introduction must state** three things: what the document covers, what prior knowledge the reader needs, and what the document does not cover.
- **Headings describe the reader's task** (e.g., "Configure the database" not "Database configuration"). Provide at least one sentence of text under every heading.
- **Progressive disclosure:** Introduce concepts from simple to complex. Define terms near where they are first needed, not all upfront.
- **Break walls of text** with lists, tables, diagrams, or code samples.

### Sample Code (Technical Writing Two)

- Code samples must be **correct, concise, and understandable.**
- Use **descriptive names** for variables, functions, and classes. Avoid abbreviations, single-letter names, and clever tricks.
- **Avoid deep nesting.** Flatten logic where possible.
- **Comment the "why,"** not the "what." Skip comments for obvious operations.
- When relevant, show **anti-examples** (what NOT to do) alongside correct examples.
- Provide **run instructions** and describe expected output.

### Illustrations (Technical Writing Two)

- **Write the caption before creating the illustration.** The caption should be brief and state the key takeaway.
- **Limit information density:** No more than one paragraph's worth of information per diagram. Split complex systems into multiple diagrams.
- **Use callouts, arrows, or highlights** to focus the reader's attention on relevant details.

---

## Rules for This Skill

- NEVER change the technical meaning or accuracy of the content. If something looks technically wrong, flag it to the user rather than silently changing it.
- NEVER add new sections, features, or content that the author did not write. Only improve expression of existing content.
- NEVER delete information — restructure or reword it instead.
- If the document is already well-written and few changes apply, say so. Do not make changes for the sake of making changes.
- When rewriting, preserve the author's voice and tone as much as possible while applying the rules.
