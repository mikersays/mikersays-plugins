---
type: Policy
title: Skill design philosophy
description: How SKILL.md files in this marketplace are written and trimmed, and the reasons.
tags: [skills, style]
generated: { by: claude-code/claude-sonnet-5-5, at: 2026-10-07T07:53:13Z }
status: draft
sources:
  - id: memory
    resource: ../../.claude/memory/skill-design-philosophy.md
    title: Preserved session context on skill design
  - id: claude-md
    resource: ../../CLAUDE.md
    title: SKILL.md format section
---

# Rules

* Write a skill as a mental model plus options, not a rigid numbered checklist. Do not assume a fixed repo layout: discover what the repo uses. The reason is that a fixed procedure makes a capable agent worse across many repos.[^memory]
* Do not add a duplicate plugin when an existing one covers the intent. Improve the existing one and add the trigger words. Example: `handoff` covered a proposed `/persist`.[^memory]
* Never cut a trigger phrase from a frontmatter `description`. It is the always-loaded matching surface, and cutting a phrase such as "I fixed it" (`/plan-close`) or "make" (`/gh-pages`) stops the skill from firing.[^memory]
* Trim the pattern "complete imperative, dash, justification clause". Keep the rule and cut the clause.[^memory]
* Keep gotchas (exact commands, flags, paths, CSS and JS pitfalls), naming contracts, output schemas, and text copied into a subagent brief or written to disk. A wrongly kept sentence costs a few tokens, and a wrongly cut one breaks the skill.[^memory]

# Frontmatter

`name` is the slash command and `description` is the one-line summary. Claude Code also reads `argument-hint`, `disable-model-invocation`, and `allowed-tools`. Codex ignores those three.[^claude-md]

An audit of all 24 skills on 2026-07-29 found the corpus about 95% lean.[^memory]

[^memory]: .claude/memory/skill-design-philosophy.md
[^claude-md]: CLAUDE.md
