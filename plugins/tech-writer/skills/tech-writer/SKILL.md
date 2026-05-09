---
name: tech-writer
description: Review and rewrite documentation in place using Google's Technical Writing guidelines
argument-hint: "[file path]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Tech Writer

Review and rewrite documentation against the conventions from Google's Technical Writing One and Two courses. Improve how content is expressed; do not change what it says.

## Process

1. **Pick the target file.** Use `$ARGUMENTS` if provided. Otherwise use the file currently in context. If neither exists, ask.
2. **Read the whole file** before editing — context matters for terminology and pronouns.
3. **Edit in place.** Preserve the author's intent, voice, and technical accuracy. Restructure and reword; do not add new content or delete information.
4. **Report changes** grouped by rule (e.g. "Active voice: 4 sentences. Filler: removed 7 phrases.").

If the document is already well-written, say so and stop. Don't churn for the sake of churn.

## Boundaries

- Don't change technical meaning. If something reads as factually wrong, flag it instead of silently fixing it.
- Don't add sections, features, or claims the author didn't write.
- Don't delete information — reword or relocate it.
- Preserve the author's voice. The goal is clarity, not homogenization.

---

## Rules with examples

The rules below come from the Google courses. Each one has a short rationale and a before/after — apply by analogy, not by pattern-matching to these exact phrases.

### Active voice

Active voice (actor + verb + target) is shorter and tells the reader who did what. Passive hides the actor.

- Before: `The error is raised when the input is divided by zero.`
- After:  `Dividing by zero raises the error.`

If a passive sentence has no actor, figure out who acts and name them. Imperatives are already active.

### Strong verbs

Forms of *be* (`is`, `are`, `was`), plus `occur` and `happen`, do little work. Replace them with verbs that name the action.

- Before: `A timeout occurs when the server is unresponsive.`
- After:  `The client times out when the server stops responding.`

Drop `There is` / `There are` openers — move the real subject to the front.

- Before: `There is a variable named count that stores the total.`
- After:  `The count variable stores the total.`

### Specific, measurable claims

Vague intensifiers (`significantly`, `much`, `very`) are noise. Use numbers when you have them.

- Before: `The new index is significantly faster.`
- After:  `The new index is 225–250% faster on the benchmark suite.`

### One idea per sentence

If a sentence has two ideas joined by `and`, `but`, or a subordinate clause that branches away from the main point, split it.

- Before: `The build runs in CI, which uses a cached image that is rebuilt nightly, and fails fast on lint errors.`
- After:  `The build runs in CI and fails fast on lint errors. CI uses a cached image, rebuilt nightly.`

When a sentence chains three or more items with `and` / `or`, lift them into a list.

### Cut filler

These phrases add length without meaning:

| Before | After |
|---|---|
| `at this point in time` | `now` |
| `is able to` | `can` |
| `in order to` | `to` |
| `causes the triggering of` | `triggers` |
| `provides a detailed description of` | `describes` |
| `due to the fact that` | `because` |

### Pronouns

Place pronouns within about five words of the noun they refer to. If another noun gets in between, repeat the original noun. After `this` or `that` used as a determiner, add the noun.

- Before: `The parser reads the config and validates the schema. It then writes it to disk.`
- After:  `The parser reads the config and validates the schema. The parser then writes the config to disk.`

- Before: `This means the request will be retried.`
- After:  `This retry policy means the request will run again.`

### Terminology

Use one term per concept across the whole document. Switching between `user`, `caller`, and `client` for the same actor forces the reader to re-map every time.

For acronyms: spell out on first use with the acronym in parentheses — **Transmission Control Protocol** (**TCP**) — then use the acronym. Skip the acronym entirely if the term appears only two or three times.

### That vs. which (US English)

`that` introduces a restrictive clause (no comma). `which` introduces a nonrestrictive clause (comma).

- `The file that you uploaded is corrupted.` (which file? the one you uploaded)
- `The file, which you uploaded yesterday, is corrupted.` (extra info about a known file)

### Lists and tables

- Bullets for unordered items, numbers for ordered steps.
- Make items grammatically parallel — same starting part of speech, same capitalization, same punctuation.
- Start numbered steps with an imperative verb: `Download the binary.` `Run the installer.`
- Introduce every list and table with a sentence that ends in a colon — often using the word "following."
- Keep table cells to two sentences or fewer; give every column a meaningful header.

Before (mixed forms):
```
- Downloading the package
- Run installer
- Configuration of the server
```

After (parallel imperatives):
```
- Download the package.
- Run the installer.
- Configure the server.
```

### Paragraphs

The opening sentence states the point — a busy reader may read only that sentence. One topic per paragraph. Aim for 3–5 sentences. A wall of seven-plus sentences usually contains two paragraphs that haven't been separated yet.

### Audience and scope

State the target audience and prerequisites near the top, and say what the document does *not* cover. Skip idioms (`hit the ground running`, `Bob's your uncle`) and culture-specific references — they trip non-native readers and add nothing.

### Self-editing pass

- Use **you**, not **we**. The reader is doing the work, not the author.
- Put conditions before instructions: `If the build fails, run make clean.` — not `Run make clean if the build fails.` Readers can skip the instruction faster when the condition comes first.
- Wrap file names, variables, commands, and class names in `code font`.

### Headings

Headings should describe the reader's task, not the topic abstractly.

- Before: `Database configuration`
- After:  `Configure the database`

Put at least one sentence of prose under every heading — orphan headings stacked together force the reader to guess what's coming.

### Sample code

Code samples should be correct, short, and readable. Use descriptive names (no `x`, `tmp`, `data2`). Flatten deep nesting. Comment *why*, not *what*. When a common mistake exists, show the anti-example next to the correct one. Include run instructions and expected output where relevant.

### Illustrations

Write the caption first — it's the takeaway. Cap each diagram at roughly one paragraph's worth of information; split complex systems across diagrams. Use callouts and arrows to direct attention.
