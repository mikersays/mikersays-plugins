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
