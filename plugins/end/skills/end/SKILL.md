---
name: end
description: Check that this session's work is finished and persisted, so the next session's agent has the context it needs, before the user closes it.
disable-model-invocation: true
allowed-tools: Bash, Read, Write, Edit
---

The user wants to close this session. Answer this question: is everything
finished and persisted, so that the next session's agent has the context it
needs?

Check each item below against this conversation and the real state of the
files and hosts. Do not answer from memory. Fix every gap you can fix without
the user, then report.

1. **Unfinished work.** List what the user asked for that is not done,
   including anything you promised to do later.
2. **Running work.** Check for background tasks and subagents still running in
   this session. For agents you started on other hosts, check their tmux
   sessions, report each result, archive its brief and report, and clean up
   anything it left running, such as simulators. If the project instructions
   describe a procedure for finishing remote agents, follow it.

   Then close every agent session that you started on another host and that
   is idle: end its tmux session, delete what a build or a download can make
   again (build output, environments, downloaded models), and remove
   worktrees whose branches are merged. Open questions for the user are not
   a reason to keep a session: record them where the project keeps open
   work, and a later session starts a new agent. Leave a session open only
   when its agent is still working or when the user said to keep it, and say
   so in the report. First make sure that unpushed work, such as a local
   branch, stays on disk and is recorded.
3. **Persistent notes.** Find where this project keeps context for later
   sessions: the project instructions file (`CLAUDE.md` or `AGENTS.md`),
   memory files, a knowledge bundle, or a docs folder. Check that it records
   what a later session needs from the following:

   - Decisions and the standing rules the user set.
   - New or changed hosts, tools, and credential key names.
   - Procedures that worked.
   - Incidents and their causes.

   If a note already covers the topic, update it. Correct anything this
   session proved wrong, and mark causes you did not confirm as unknown. Track
   open work where the project tracks tasks. Never record a secret value. If
   the notes have an index or a validator, run it after you add or move
   anything.
4. **Project docs.** For each repository you worked in, check that its README,
   docs, and any knowledge bundle match the work.
5. **Git.** Run `git status` in each repository you touched, and in the
   working directory. Commit what belongs in the history. Push only as the
   project instructions allow; if they say nothing, do not push.
6. **Cleanup.** Remove temporary files that hold private data, and close any
   connections, processes, or sessions you opened and no longer need.

Then give the user a short report:

- Start with a clear answer: ready to close, or not ready and why.
- List what you fixed during this check.
- List what still needs the user, such as a decision or an approval.

If nothing is missing, say so in one or two sentences. Do not end the session
yourself: tell the user to type `/exit`.
