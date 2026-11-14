# end

Check that a session is finished and persisted before you close it.

## Usage

```
/end
```

Run it when you are ready to close a session. The skill checks the real state
of the conversation, files, and hosts, fixes every gap it can, and reports
whether the session is ready to close. It never ends the session itself: when
everything is in order, it tells you to type `/exit`.

## What it checks

1. **Unfinished work** — requests not done and promises to do later.
2. **Running work** — background tasks, subagents, and agents on other hosts.
3. **Persistent notes** — decisions, rules, hosts, tools, procedures, and
   incidents recorded where the next session will read them.
4. **Project docs** — READMEs, docs, and knowledge bundles match the work.
5. **Git** — repositories you touched are committed. It pushes only when the
   project instructions allow it.
6. **Cleanup** — private temporary files removed and opened connections closed.

## Output

A short report: ready or not ready (and why), what the skill fixed, and what
still needs you.

## Relation to `handoff`

`/handoff` helps you decide what context to save and where. `/end` is the
final gate: it verifies that all work and context are saved, and fixes gaps.
It only runs when you invoke it.
