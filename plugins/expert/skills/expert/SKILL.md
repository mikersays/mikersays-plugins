---
name: expert
description: >-
  Take a task the user describes and produce a deeper version of it, not a bigger one. Analyze what a
  top professional in the field would do that the user did not ask for, the raw material they would
  start from, the specific methods and tools they would use, and what independent evidence would show
  the result is right. Then rewrite the prompt to ask for exactly that. Use when the user runs
  /expert followed by a task description.
argument-hint: "[task description]"
disable-model-invocation: true
---

# Expert

The user wants a **deeper** version of a task, not a **bigger** one. Depth means better judgment,
better inputs, better methods, and real verification. It does not mean more deliverables, more
sections, or more scope.

## Input

The task is the text after `/expert`. If the user gave none, look at their most recent request in the
conversation. If there is no task at all, ask for one in a single line and stop.

Do not start the task. Do not answer it. Your job is to analyze it and rewrite the prompt.

## Process

Name the field first (for example "forensic accountant", "pediatric nurse", "backend engineer",
"documentary editor"), then answer the four questions below about the user's task.

1. **What a top professional would do that the user is not asking for.** Consider the steps, checks,
   questions, and judgment calls an expert performs by habit. Examples: clarify the real goal behind
   the request, test assumptions, look for failure modes, decide what to leave out. Keep only items
   that change the quality of the result.
2. **The rawest material they would start from.** Name primary sources: original data, source code,
   filings, interviews, logs, specimens, raw measurements, first-hand documents. Contrast each with
   the digested version the user is likely relying on (summaries, blog posts, secondhand reports,
   AI-written overviews).
3. **The specific methods and tools they would use.** Name concrete techniques, frameworks, software,
   commands, libraries, or instruments, not categories. "Run a differential diagnosis" and "profile
   with `perf`" qualify. "Use best practices" does not.
4. **What, other than you or me, would show the result is right.** Name evidence that is independent
   of the user and of Claude: a test suite that runs, a reconciliation against a source of record, a
   reference implementation, a published benchmark, a domain expert's checklist, a measurement in the
   real world, a reproduction by someone else. Self-review and "it looks right" do not count. If no
   independent check exists, say so and name the closest substitute.

Ground the answers in the task. If you can check something in the user's environment (files, repo,
tools installed), do so rather than guessing. If a fact is unknown, say it is unknown. Do not invent
sources, tools, or standards.

## Output

Use this layout and nothing else:

**Field:** the professional role you are modeling.

**1. What an expert would do that you didn't ask for** — short bullets.

**2. Rawest material** — short bullets, each as `raw source` instead of `digested version`.

**3. Methods and tools** — short bullets of specific names.

**4. Independent proof** — short bullets of checks that neither the user nor Claude can fake.

**Rewritten prompt**

A single prompt in a fenced code block, written in the user's voice, that asks for exactly the
findings above. It must:
- Keep the user's original goal and scope. Add depth, not deliverables.
- Point to the raw material by name and tell the agent to start there.
- Name the methods and tools.
- State the independent proof the result must pass, and ask the agent to report the outcome of each
  check.
- Be self-contained, so it works pasted into a fresh session.

End with one line asking whether to run the rewritten prompt now. Do not run it without a yes.

## Rules

- Be specific over thorough. Four sharp bullets beat ten generic ones.
- Do not widen the task. If an item adds scope rather than depth, drop it.
- Never present a guess as an established standard, tool, or source.
- Keep the whole response short enough to read in one screen where the task allows.
