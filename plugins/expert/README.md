# expert

Rewrite a task prompt so it asks for a deeper result, not a bigger one.

## Usage

```
/expert [task description]
```

Describe a task after the command. The skill does not do the task. It analyzes the task the way a top
professional in that field would, then rewrites your prompt to ask for exactly that.

## What it does

For your task, it states:

1. **What a top professional would do that you are not asking for.** The habits, checks, and judgment
   calls that change the quality of the result.
2. **The rawest material they would start from.** Primary sources instead of the digested summaries
   you may be relying on.
3. **The specific methods and tools they would use.** Named techniques and software, not categories.
4. **What would show the result is right, other than you or Claude.** Independent evidence such as a
   running test suite, a reconciliation against a source of record, or a reproduction by someone else.

It then writes a self-contained replacement prompt that asks for those four things, and asks whether
to run it.

## Depth, not size

The rewritten prompt keeps your original goal and scope. It adds better inputs, methods, and
verification. It does not add deliverables.

## Origin

Based on a prompt pattern shared as "A simple prompt that often helps me."
