---
name: skill-design-philosophy
description: "How Mike wants SKILL.md instructions written in this marketplace — judgment over checklists, repo-adaptive"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: cdfd9b6d-0185-4c39-9659-a7b664f10d0c
---

When writing or revising skills in the mikersays-plugins marketplace, Mike prefers instructions that are **not overbearing on the agent**: trust the agent to use judgment and adapt to the actual repo structure rather than marching through a rigid numbered checklist or assuming a fixed layout (e.g. don't presume `docs/plan/` or `docs/issues/` exist — discover what the repo actually uses and route to its own conventions).

**Why:** the agent is smart and a fixed procedure makes it dumber and produces worse fits across the many repos a skill runs in.

**How to apply:** frame steps as a mental model + options, explain the *why*, scale effort to what actually happened, and keep only genuine guardrails as hard rules. Also: avoid creating duplicate plugins — if an existing one already covers the intent (e.g. `handoff` covered a proposed `/persist`), improve it and fold the trigger words in instead.

## When trimming a skill for token bloat

A full audit of all 24 skills (2026-07-29) found the corpus ~95% lean. Two rules came out of it:

**The frontmatter `description` is the always-loaded, skill-matching surface — never cut a trigger phrase from it.** Removing mechanics recaps is safe (the body specifies them authoritatively at run time). Removing a phrase like `"I fixed it"` from `/plan-close` or `"make"` from `/gh-pages` silently stops the skill from firing, which is far worse than a few extra tokens. Adversarial review rejected nearly every proposed description trim on these grounds.

**The real bloat pattern is a complete imperative followed by a dash and a justification clause** — "Leave at least 20px between any two nodes — touching shapes read as one blob." Agents follow instructions; they don't need persuading. Cut the clause, keep the rule.

What is *not* bloat, and was repeatedly proposed for cutting and rejected: specific gotchas (exact commands, flags, paths, CSS/JS pitfalls), naming contracts, output schemas, and text copied verbatim into a subagent brief or written to disk. A wrongly-kept sentence costs a few tokens; a wrongly-cut one breaks the skill.
