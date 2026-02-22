# tech-writer

Review and rewrite documentation using Google's Technical Writing One and Two guidelines.

## Usage

```
/tech-writer path/to/document.md   # review a specific file
/tech-writer                       # review the file currently in context
```

## What it does

1. Reads the target document
2. Applies all rules from Google's Technical Writing One and Two courses
3. Rewrites the file in place with improvements
4. Reports a summary of changes grouped by rule category

## Rules applied

- **Words & Terminology** — consistent terms, proper acronyms, clear pronouns
- **Active Voice** — convert passive to active, name the actor
- **Clear Sentences** — strong verbs, no "there is/are," measurable data over vague adjectives
- **Short Sentences** — one idea per sentence, extract embedded lists, remove filler
- **Lists & Tables** — parallel structure, imperative verbs, introductory sentences
- **Paragraphs** — strong openers, single topic, 3–5 sentences
- **Audience** — state the audience, avoid idioms, explain jargon
- **Document Organization** — scope, prerequisites, key points first
- **Self-Editing** — second person, conditions before instructions, code font
- **Large Documents** — outlines, task-based headings, progressive disclosure
- **Sample Code** — correct, concise, descriptive names, comment the "why"
- **Illustrations** — captions first, limited density, callouts for focus

## Subagent

The plugin also registers a `tech-writer` Task agent. Claude can spawn it autonomously to review docs in the background:

```
Task(subagent_type="tech-writer", prompt="Review plugins/ship/README.md")
```

The agent uses Sonnet for fast, cost-effective reviews and has access to Read, Write, Edit, Glob, and Grep tools.

## Installation

```bash
/plugin install tech-writer@mikersays-plugins
```
