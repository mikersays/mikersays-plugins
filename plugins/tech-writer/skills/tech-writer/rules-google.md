# Google Technical Writing rules

Review and rewrite documentation against the conventions from Google's Technical Writing One and Two courses, plus a set of clarity rules adapted from ASD-STE100 Issue 9. Improve how content is expressed; do not change what it says.

## Process

1. **Read the whole file** before editing — context matters for terminology and pronouns.
2. **Edit in place.** Preserve the author's intent, voice, and technical accuracy. Restructure and reword; do not add new content or delete information.
3. **Report changes** grouped by rule — for example, "Active voice: 4 sentences. Filler: removed 7 phrases."

If the document is already well-written, say so and stop. Don't churn for the sake of churn.

## Boundaries

- Don't change technical meaning. If something reads as factually wrong, flag it instead of silently fixing it.
- Don't add sections, features, or claims the author didn't write.
- Don't delete information — reword or relocate it.
- Preserve the author's voice. The goal is clarity, not homogenization.

---

## Rules with examples

Apply these rules by analogy, not by pattern-matching to these exact phrases.

### Active voice

Rewrite passive sentences in the active voice: actor + verb + target.

- Before: `The error is raised when the input is divided by zero.`
- After:  `Dividing by zero raises the error.`

If a passive sentence has no actor and the document establishes who acts, name them. If it doesn't, see *Don't invent an actor* below. Imperatives are already active.

### Modal passives

`can be changed`, `must be rotated`, `is to be installed`, and `will be applied` are passives wearing a modal. Test a verb by asking "by whom or by what?" where the grammatical subject is not the thing acting — a literal `by` phrase is the strongest signal, a missing but recoverable actor the next. An active sentence whose subject already performs the action is not passive, however easily you can name the actor. In a procedure, rewrite as an imperative; in prose, name the actor.

- Before: `The log level can be changed in config.yaml, and the API token must be rotated every 90 days.`
- After:  `You can change the log level in config.yaml. Rotate the API token every 90 days.`

The frame `X is used by Y to do Z` is the same problem wearing a different coat. Delete the frame and promote the real verb.

- Before: `These headers are used by the proxy to route the request.`
- After:  `The proxy routes the request with these headers.`

### Don't invent an actor

Naming the actor is only an improvement when you know who the actor is. If the real cause is unestablished, keep the passive in descriptive prose or use an indefinite subject. A fabricated actor assigns a cause nobody confirmed — that's a change to technical meaning, not a style fix.

- Before: `Replication corrupted the row.` (the source said only that the row was corrupted during replication)
- After:  `During replication, something corrupted the row.`

### Strong verbs

Forms of *be* (`is`, `are`, `was`), plus `occur` and `happen`, do little work. Replace them with verbs that name the action.

- Before: `A timeout occurs when the server is unresponsive.`
- After:  `The client times out when the server stops responding.`

Drop `There is` / `There are` openers — move the real subject to the front.

- Before: `There is a variable named count that stores the total.`
- After:  `The count variable stores the total.`

### Nominalizations

Put the action back in the verb. Watch for `gives an indication of`, `performs a completion of`, `do a reboot of`, and `before the deletion of`.

- Before: `The health endpoint gives an indication of cluster state. Before the deletion of the namespace, confirm the completion of the backup job.`
- After:  `The health endpoint shows the cluster state. Before you delete the namespace, confirm that the backup job finished.`

### Lead with the action, not the tool

`Use X to do Y` buries the real task behind `use`. Name the action and put the tool in a `with` phrase.

- Before: `Use the migrate CLI to apply the pending schema changes.`
- After:  `Apply the pending schema changes with the migrate CLI.`

### Specific, measurable claims

Vague intensifiers (`significantly`, `much`, `very`) are noise. Use numbers when you have them.

- Before: `The new index is significantly faster.`
- After:  `The new index is 225–250% faster on the benchmark suite.`

### One idea per sentence

If a sentence has two ideas joined by `and`, `but`, or a subordinate clause that branches away from the main point, split it.

- Before: `The build runs in CI, which uses a cached image that is rebuilt nightly, and fails fast on lint errors.`
- After:  `The build runs in CI and fails fast on lint errors. CI uses a cached image, rebuilt nightly.`

When a sentence chains three or more items with `and` / `or`, lift them into a list.

### Chained and dangling participles

Chained `-ing` phrases and participial modifiers detach actions from their subject. Break it into a short lead-in, a numbered list of imperative steps, and a separate sentence for the consequence.

- Before: `Engineers deploying to production without running the pending migration and forgetting to drain the load balancer risk dropping in-flight requests and corrupting the audit log.`
- After:  `Before you deploy to production: 1. Run the pending migration job. 2. Drain connections from the load balancer. If you skip these steps, the deploy can drop in-flight requests and damage the audit log.`

A participle dangles when its implied subject isn't the subject of the sentence. Give the clause its own subject.

- Before: `After running the migration, the load balancer must be drained.` (the load balancer didn't run the migration)
- After:  `After you run the migration, drain the load balancer.`

### Complete sentences

Don't shorten a prose sentence by deleting the thing it is about. Every sentence names its own subject and its own verb, even when a heading appears to supply them. The same goes for a bare condition: name the noun the condition tests. This applies to prose, not to list items that continue a lead-in or to reference-table cells, where fragments are correct and parallelism matters more.

- Before: `Can be a maximum of 64 characters.` / `Log level to DEBUG.` / `If enabled, remove the proxy variables.`
- After:  `A bucket name can have a maximum of 64 characters.` / `Set the log level to DEBUG.` / `If the proxy variables are configured, remove them.`

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

### Articles

Never delete an article to save a word. Repeat the article when its absence would let two nouns read as one thing, or would let a leading adjective silently spread across a whole series. Conversely, drop the article before a noun followed by an alphanumeric identifier — `pod web-7f3a`, `ticket OPS-1421` — because the noun plus identifier already works as a name. This does not extend to a noun modified by a file, variable, or flag name: `the config.yaml file` and `the count variable` keep their articles.

- Before: `Delete the branch and tag. Install the new certificate, private key, and CA bundle. Restart the pod web-7f3a and check the ticket OPS-1421.`
- After:  `Delete the branch and the tag. Install the new certificate, the private key, and the CA bundle. Restart pod web-7f3a and check ticket OPS-1421.`

### Terminology

Use one term per concept across the whole document. Switching between `user`, `caller`, and `client` for the same actor forces the reader to re-map every time.

For acronyms: spell out on first use with the acronym in parentheses — **Transmission Control Protocol** (**TCP**) — then use the acronym. Skip the acronym entirely if the term appears only two or three times.

### Stacked noun modifiers

Keep a noun phrase to about three words. When it grows past that, break it apart with `of`, `in`, `for`, or a relative clause, and drop any modifier the reader doesn't need to identify the thing. Established terms are exempt — `dead letter queue`, `continuous integration pipeline`, and `cross-site request forgery token` are the names readers search for, so leave them whole and count each as one term.

- Before: `Update the Kubernetes cluster node pool autoscaler configuration file.`
- After:  `Update the configuration file for the node pool autoscaler in the Kubernetes cluster.`

### Hyphenate compound modifiers

When two or more words act as a single adjective in front of a noun, hyphenate them. Hyphenation groups a phrase; it does not shorten one. Don't use it to slip an over-long noun stack past the three-word guidance.

- Before: `Set the connection pool idle timeout value, then drain the message queue dead letter replay worker.`
- After:  `Set the connection-pool idle-timeout value, then drain the dead-letter replay worker for the message queue.`

Never re-punctuate a product, flag, or API name that already has a canonical spelling.

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

### Work steps

Give each action its own numbered step. Keep two actions in one step only when the reader performs them at the same moment, or when a check and its pass criterion belong together. Don't mix statements about what the system does on its own into a list of things the reader must do, and drop `you must` in front of a step — `Stop the daemon` already says it.

- Before: `3. Stop the collector service and remove the stale lock file from /var/run. 4. The snapshot job copies the volume to S3. 5. You must then verify the checksum.`
- After:  `3. Stop the collector service. 4. Remove the stale lock file from /var/run. 5. Verify the checksum.` — with `The snapshot job copies the volume to S3.` moved out of the list into the surrounding prose, because it describes what the system does, not what the reader does.

### Notes carry no instructions

Keep notes to background. Move instructions, prerequisites, limits, and tolerances into the numbered step they belong to — a tolerance belongs on the same line as the measurement that has to meet it, not below it.

- Before: `NOTE: The service account must hold roles/storage.admin before the sync starts. 1. Start the sync job. 2. Run the health check. NOTE: The total time must not exceed 0.2 s.`
- After:  `1. Confirm that the service account holds roles/storage.admin. 2. Start the sync job. 3. Run the health check. The total time must not exceed 0.2 s.` — every note here carried a requirement, so nothing is left to keep as a note. Don't invent background to fill the gap.

To test a procedure, read it with every note deleted. If the reader can no longer finish the task, a note is carrying load it shouldn't carry.

### Warnings

Label a hazard before the reader reaches it, lead with the action, then say what happens if they ignore it. Grade the label to the real worst case rather than the visible symptom — irreversible data loss outranks a recoverable restart — and name the concrete failure: `critical` and `essential` tell the reader that someone cared, not what to avoid. If the warning only applies under a condition, the condition goes first.

- Before: `Run dbctl reset --env prod to reinitialize the schema. Note that proper handling of production databases is essential, as this drops every table first.`
- After:  `**Warning:** Do not run dbctl reset --env prod against a live database. The command drops every table before it recreates the schema, and the data is unrecoverable without a backup. To reinitialize a non-production schema, run dbctl reset --env <name>.`

### Paragraphs

The opening sentence states the point — a busy reader may read only that sentence. One topic per paragraph. Aim for 3–5 sentences. A wall of seven-plus sentences usually contains two paragraphs that haven't been separated yet.

### Transitions

Splitting long sentences strips out the causal and temporal links that were holding them together, and readers left to infer a relationship often infer the wrong one. Put the relationship back with an explicit connector — `then`, `as a result`, `at the same time`. When a follow-up sentence points back at the previous one, name what it points at instead of leaving a bare `this`.

- Before: `The load balancer marks the node unhealthy. The scheduler moves the pods. Record the schema version before you migrate. This helps later.`
- After:  `The load balancer marks the node unhealthy. As a result, the scheduler moves the pods to another node. Record the schema version before you migrate. This record lets you roll the database back to a known state.`

### Audience and scope

State the target audience and prerequisites near the top, and say what the document does *not* cover. Skip idioms (`hit the ground running`, `Bob's your uncle`) and culture-specific references.

### Latin abbreviations

`e.g.`, `i.e.`, and `etc.` cost non-native readers a lookup, and `etc.` hides information the reader may actually need. Spell out the English equivalent — `for example`, `that is`. Where `etc.` hides items you cannot recover from the document, keep the visible items, mark the list as partial, and flag the gap to the author. Never complete a list from memory.

- Before: `Set the log level (i.e., debug, info, etc.) in config.yaml.`
- After:  `Set the log level in config.yaml. The permitted values include debug and info — confirm the full set with the author.`

### Self-editing pass

- Use **you**, not **we**. The reader is doing the work, not the author.
- Put conditions before instructions: `If the build fails, run make clean.` — not `Run make clean if the build fails.`
- Wrap file names, variables, commands, and class names in `code font`.

### Headings

Headings should describe the reader's task, not the topic abstractly.

- Before: `Database configuration`
- After:  `Configure the database`

Put at least one sentence of prose under every heading.

### Sample code

Code samples should be correct, short, and readable. Use descriptive names (no `x`, `tmp`, `data2`). Flatten deep nesting. Comment *why*, not *what*. When a common mistake exists, show the anti-example next to the correct one. Include run instructions and expected output where relevant.

### Illustrations

Write the caption first — it's the takeaway. Cap each diagram at roughly one paragraph's worth of information; split complex systems across diagrams. Use callouts and arrows to direct attention.

---

## Output format

After rewriting the file, return a summary structured like this:

```
## Changes Applied

### Words & Terminology
- [list specific changes]

### Active Voice
- [list specific changes]

### Clear Sentences
- [list specific changes]

### Notes & Warnings
- [list specific changes]

...and so on for each category where changes were made.

### No Changes Needed
- [list categories where the document already followed the guidelines]
```

## Source and attribution

The clarity rules adapted here are paraphrased from **ASD-STE100 Issue 9**, © ASD. This plugin is not affiliated with or endorsed by ASD.
