---
name: ste
description: Rewrite documentation into Simplified Technical English following the rules of ASD-STE100 Issue 9. Use when asked for STE, Simplified Technical English, controlled language, or docs that must survive translation and non-native readers.
argument-hint: "[file path]"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Simplified Technical English

Rewrite a document into Simplified Technical English (STE), the controlled language defined by ASD-STE100. STE is not a style preference. It is a restricted subset of English — a fixed vocabulary, six verb forms, and hard sentence-length limits — designed so that a procedure means exactly one thing to a reader whose English is weak, to a translator, and to a machine.

STE output is meant to look constrained. Short declarative sentences, repeated nouns, and no variety for variety's sake are the point, not a failure of the rewrite.

## When to use this, and when not to

Use `/ste` for:

- Safety-critical procedures, runbooks, and incident playbooks.
- Installation, maintenance, and operating instructions.
- Documents headed for translation, or written for readers with limited English.
- Anywhere a misread step costs money, hardware, or a person.

Do not use `/ste` for marketing pages, conceptual essays, changelogs, blog posts, or anything where natural register matters.

**This skill deliberately contradicts `/tech-writer`.** They encode two different standards. Never run both over the same file, and never "fix" STE output with `/tech-writer` — see [Where STE and /tech-writer disagree](#where-ste-and-tech-writer-disagree).

## Process

1. **Pick the target file.** Use `$ARGUMENTS` if given. If that path does not exist, run Glob for similar filenames and confirm with the user before you edit anything. Otherwise use the file in context. If neither exists, ask.
2. **Read the whole file**, then classify every block as **procedural**, **descriptive**, or **safety**. The rules differ by class, and applying the wrong class is the most common way to get STE wrong.
3. **Rewrite in place, class by class.** Where a substitution will not fit, rebuild the sentence (rule 9.1a). Do not force a word-for-word swap that damages the meaning.
4. **Report by rule group.** Include a word count for any sentence at or over its cap, and list every term you could not convert without changing the meaning.

## Boundaries

- Never change technical meaning. Flag anything that reads as factually wrong; do not silently fix it.
- Never invent an actor to satisfy the active-voice rule (3.6h).
- Never alter quoted text, UI strings, command names, or flag spellings (1.14a).
- Never add or delete information. Restructure and reword.
- This skill does **not** contain the ASD approved-word dictionary and cannot check a word's approval status against it. Where approval status matters and you are unsure, reason from the technical-noun and technical-verb categories, apply the rule, and flag the uncertainty in the report.

---

## 1. Words

**1.1 — Three legal sources.** Every word must be an approved dictionary word, a technical noun, or a technical verb. If a word qualifies under none of the three, rewrite the sentence with words that do.

- Before: `Utilize the CLI to ascertain whether the indexing daemon is functioning.`
- After: `Find if the indexing daemon operates correctly with the CLI.`

**1.2 — One word, one part of speech.** Use each approved word only in the part of speech the dictionary assigns it. If the word is approved as a noun but not as a verb, build the sentence around the noun.

- Before: `Test the API response against the schema.`
- After: `Do a test of the API response against the schema.`

**1.2a — Rebuild, don't swap.** When the approved replacement sits in a different part of speech, restructure the sentence around it rather than dropping it into the old slot. Re-read the result and confirm the meaning held.

- Before: `Make sure that the migration tool is operable before you upgrade.`
- After: `Make sure that the migration tool can operate before you upgrade.`

**1.3 — One word, one meaning.** Use each approved word only in the single sense the dictionary gives it, even where ordinary English allows more. Reject a word whose everyday sense fits but whose approved sense does not.

- Before: `Follow the steps in the installation guide.`
- After: `Obey the steps in the installation guide.`

**1.4 — Approved forms only.** Use only the inflected forms the dictionary prints: for verbs, the infinitive/imperative, simple present, simple past, and past participle; for adjectives, the base, comparative, and superlative. Do not coin a form.

**1.5 — Technical nouns.** A domain word absent from the dictionary is still legal when it falls into one of the standard's technical-noun categories — among them parts, tools, materials, systems, facilities, units of measurement, engineering and mathematics terms, computing and ICT terms, documents, roles and organizations, quoted text, colors, and damage states. Check the category before you use the word.

- Before: `Move the pointer to the small picture on the display, then push the button on the hand-held input device.`
- After: `Move the cursor to the icon, then click the mouse.`

**1.5a — Colors are states, not scales.** Treat color words as technical nouns and never grade them.

- Before: `The status LED becomes greener as the write buffer drains.`
- After: `The status LED changes from yellow to green when the write buffer is empty.`

**1.6 — Unapproved words inside technical nouns.** A word the dictionary marks unapproved may still appear as part of a technical noun. In any other use, replace it.

**1.7 — Never verb a technical noun.** Keep it in the noun slot and express the action with an approved verb. The one carve-out: a word that independently qualifies under both a technical-noun category (1.5) and a technical-verb category (1.12) may be used as either — `use a carbide drill` and `drill a hole at the intersection` are both conformant.

- Before: `Email the incident report to the on-call engineer.`
- After: `Send the incident report to the on-call engineer by e-mail.`

**1.8 — Use the established name.** Where your company, industry, or subject field already has a settled name for a component or process, use exactly that name. Do not invent your own.

- Before: `Restart the box that runs the scheduler.`
- After: `Restart the control-plane node that runs the scheduler.`

**1.9 — Coin short, self-explanatory terms.** Where you must invent a term, keep it to three words or fewer. Drop any modifier the reader does not need to identify the item.

- Before: `Update the primary regional PostgreSQL relational database management system instance configuration file (3).`
- After: `Update the database configuration file (3).`

**1.10 — No slang, no in-group jargon.** Choose the term a reader outside your team or region will recognize.

- Before: `If the deploy goes sideways, roll back and nuke the pods.`
- After: `If the deployment fails, do the rollback and delete the pods.`

**1.11 — One item, one name.** Once you choose a term, never switch to a synonym or a shortened variant later in the document.

- Before: `1. Confirm that the job runner is idle. 2. Restart the worker. 3. Check the executor logs.`
- After: `1. Confirm that the worker is idle. 2. Restart the worker. 3. Check the worker logs.`

**1.12 — Technical verbs.** A verb absent from the dictionary is legal when it belongs to one of the technical-verb categories: manufacturing processes, computer processes and applications, subject-field instructions, and law or regulation. It must still obey every other verb rule.

- Before: `Do the start of the operating system again after the update finishes.`
- After: `Reboot the operating system after the update finishes.`

**1.12a — Prefer the ordinary approved verb.** Spend a specialized technical verb only where the ordinary vocabulary cannot express the action.

- Before: `Validate that the configuration file exists before you start the service.`
- After: `Make sure that the configuration file exists before you start the service.`

**1.12b — Be exact.** Where you do need a technical verb, pick the one that names the precise operation, not a broad catch-all.

- Before: `Process the source image to 8-bit indexed color.`
- After: `Convert the source image to 8-bit indexed color.`

**1.12c — Never verb a tool, part, or material,** unless that word also qualifies on its own under a technical-verb category (see 1.7). Otherwise use an approved verb plus a technical noun.

- Before: `Firewall the management port on every edge node.`
- After: `Block the management port on every edge node with the firewall.`

**1.12d — Subject-field sense only.** A word admitted as a technical verb is legal only in the sense that qualified it. Its unrelated everyday senses stay out.

**1.13 — Technical verbs stay verbs.** Un-nominalize any construction that parks the action in a noun.

- Before: `Do a reboot of the API gateway after the certificate rotation.`
- After: `Reboot the API gateway after you rotate the certificate.`

**1.13a — Participles as adjectives.** The past participle of a technical verb may stand as an adjective in front of a noun; the result is itself a technical noun.

- Before: `Verify the checksum of the data that the agent has encrypted.`
- After: `Verify the checksum of the encrypted data.`

**1.14 — American spelling**, matching the dictionary, unless a contract or an official style directive requires otherwise.

- Before: `Initialise the analyser, then set the colour scheme in the behaviour profile.`
- After: `Initialize the analyzer, then set the color scheme in the behavior profile.`

**1.14a — Quoted text is untouchable.** Reproduce on-screen labels, UI strings, flags, and command names exactly, even where their spelling differs from the document's convention.

- Before: `In the toolbar menu, click Customize Toolbar.` (the button reads `Customise Toolbar`)
- After: `In the toolbar menu, click "Customise Toolbar".`

## 2. Multi-word nouns

**2.1 — Three words maximum.** Cap a noun phrase at three words. Where a stack grows past three, break it apart with a preposition or a relative clause so the reader can see which modifier attaches to which noun.

- Before: `Update the Kubernetes cluster node pool autoscaler configuration file.`
- After: `Update the configuration file of the node pool autoscaler in the Kubernetes cluster.`

**2.2 — Two methods for long official terms.** Where an official term runs longer than three words and cannot be reworded, write it in full at first mention, then either introduce a short form (method 1) or hyphenate the words that bind (method 2).

**2.2a — Method 1, first-mention expansion.** Write the long term in full, explain it if the surrounding text does not, and give the short form you will use from then on. Use that short form consistently.

- Before: `The RTPA batches samples and forwards them to the export pipeline every 30 seconds.`
- After: `The Realtime Telemetry Pipeline Aggregator (RTPA) batches samples and sends them to the metrics export pipeline every 30 seconds. The RTPA holds a maximum of 10,000 samples in memory.`

**2.2b — Do not abbreviate short terms, and keep abbreviations out of steps.** Spell terms out inside work steps and part lists.

- Before: `1. Stop the ARS. 2. Delete the CQ from the ARS. 3. Restart the ARS.`
- After: `1. Stop the archive service. 2. Delete the cleanup queue from the archive service. 3. Restart the archive service.`

**2.2c — Method 2, hyphenation.** Hyphenate the words inside a noun stack that act together as a single modifier. A hyphenated compound counts as one word, so hyphenation can bring an over-long term back under the three-word limit.

- Before: `Set the connection pool idle timeout value in server.toml.`
- After: `Set the connection-pool idle-timeout value in server.toml.`

**2.2d — Hyphenate only what binds.** Never chain a whole noun stack into one string. Where you cannot tell which words bind, remove the hyphens, explain the term, and introduce a short form instead.

- Before: `Restart the message-queue-dead-letter-replay-worker process.`
- After: `Restart the message-queue dead-letter-replay worker.`

**2.2e — Leave approved terms alone.** Do not add hyphens to an approved term of three words or fewer, and do not strip hyphens out of one that already has them.

- Before: `Enable the feature-flag service, then set the write ahead log path.`
- After: `Enable the feature flag service, then set the write-ahead log path.`

## 3. Verbs

**3.1 — Approved verbs, approved inflections.** Use only the verbs the dictionary lists, in only the forms it prints. Do not coin a verb or an inflection.

- Before: `The platform sunsets the v1 endpoint on 1 June, and the proxy transparently backfills the missing fields.`
- After: `We remove the v1 endpoint on 1 June. The proxy adds the missing fields.`

**3.2 — Six verb shapes only:** infinitive, imperative, simple present, simple past, simple future, and past participle used as an adjective. No perfect tenses, no progressives, no other multi-word tense.

- Before: `The agent has been polling the queue since startup, and by the time the alert fired it had already retried three times.`
- After: `The agent polls the queue after startup. The agent retried three times before the alert started.`

**3.3a — Participles state a condition.** A past participle may state the condition of a thing, directly in front of the noun or after `be`, `become`, or `stay`. That is an adjective, not passive voice. Do not "fix" it into an active construction.

- Before: `Review every file that has been modified before you commit, and confirm that the cache has been cleared.`
- After: `Review each modified file before you commit. Then make sure that the cache is clear.`

**3.3b — Participial adjectives need adjective approval.** Use a participial adjective only where the dictionary lists that word as an adjective.

- Before: `Restart the deprecated worker and replace the truncated payload.`
- After: `Restart the old worker and replace the damaged payload.`

**3.4a — No perfect tenses.** State the fact in the simple past or the simple present.

- Before: `The migration script has created the index, and the replica has already caught up.`
- After: `The migration script created the index. The replica is now current.`

**3.4b — No modal passives.** `can be changed`, `must be rotated`, `is to be installed`, `will be applied` — all out. Rewrite as an imperative in a procedure, or name the actor and use an active modal in a description.

- Before: `The log level can be changed in config.yaml, and the API token must be rotated every 90 days.`
- After: `You can change the log level in config.yaml. Rotate the API token every 90 days.`

**3.5a — No progressive `-ing` verbs.** Use the simple present, the simple past, or an imperative.

- Before: `While the container is starting, the health check is returning 503.`
- After: `During startup, the health check returns 503.`

**3.5b — No chained participles.** Never build a sentence from stacked `-ing` phrases and participial modifiers. Split it into a short lead-in, numbered imperative steps, and a separate statement of the consequence.

- Before: `Engineers deploying to production without running the pending migration and forgetting to drain the load balancer risk dropping in-flight requests.`
- After: `Before you deploy to production, do these steps: (1) Run the pending migration job. (2) Drain the connections from the load balancer. If you do not do these steps, the deploy can drop in-flight requests.`

**3.5c — Gerund nouns are permitted in headings.** An `-ing` word is legal as a standalone technical noun naming a procedure, typically as a heading. Keep it to the bare noun. This is a permission, not a requirement — an imperative heading is also legal STE.

- Before: `## Package and ship the release artifacts`
- After: `## Packaging and Shipping`

**3.5d — Keep `-ing` inside established function names.** `caching layer`, `logging framework`, `load-balancing policy` are technical nouns. Do not unpack them into relative clauses.

- Before: `Configure the layer that does caching, then attach the policy that balances load to the gateway.`
- After: `Configure the caching layer. Then attach the load-balancing policy to the gateway.`

**3.5e — Everything else `-ing` gets rewritten.** Outside technical nouns and their modifiers, only the small closed set of `-ing` words the dictionary approves is legal.

- Before: `Confirm the mounting of the volume and the seeding of the database before the starting of the service.`
- After: `Make sure that the volume is available and that the database contains the initial data. Then start the service.`

**3.6a — Active voice.** The grammatical subject is the thing that performs the action. Keep the passive only in descriptive text where the agent is genuinely unknown.

**3.6b — The "by whom or by what?" test.** Ask it of the verb where the grammatical subject is not the thing acting. A literal `by` phrase is the strongest signal; a missing but recoverable actor is the next. An active sentence whose subject already performs the action is not passive, however easily you can name the actor. Make the answer the subject.

**3.6c — Repair method 1: promote the named agent.** Where the agent already appears after `by`, make it the subject and drop the `by` phrase.

- Before: `The TLS certificates are renewed by the cron job every Sunday at 02:00.`
- After: `The cron job renews the TLS certificates every Sunday at 02:00.`

**3.6d — Repair method 2: delete the empty frame.** `X is used by Y to do Z` — delete the frame, make Y the subject, promote the real verb.

- Before: `These headers are used by the proxy to route the request to the correct shard.`
- After: `The proxy routes the request to the correct shard with these headers.`

**3.6e — Repair method 3: make it an imperative.** In procedural text, address the reader and start the step with the action verb.

- Before: `The cache is to be cleared and the feature flag is to be disabled before the deployment is started.`
- After: `Before you deploy, do these steps: 1. Clear the cache. 2. Set the feature flag to OFF.`

**3.6f/g — Repair method 4: supply the missing agent.** Use `you` where the reader acts, and `we` where the publishing organization acts.

- Before: `Compression is not applied to files that are already archived.`
- After: `We do not compress files that are already archived.`

**3.6h — Never manufacture an agent.** Where the true cause is unknown, keep the passive in descriptive text or use an indefinite subject. A fabricated actor asserts a cause nobody confirmed, which is a change to technical meaning.

- Before: `Replication corrupted the row.` (the source said only that the row was corrupted during replication)
- After: `During replication, something corrupted the row.`

**3.6i — Classify before you rewrite a modal passive.** Decide whether the sentence is a procedure or a description, then choose deliberately: an imperative for the procedure, a named subject with an active modal for the description.

**3.7a — Action in the verb, not the noun.** `gives an indication of` → `shows`; `before the removal of` → `before you remove`.

- Before: `The health endpoint gives an indication of the state of the cluster.`
- After: `The health endpoint shows the state of the cluster.`

**3.7b — Where the word is not an approved verb, use a verb frame.** Typically `do a <noun> of`.

- Before: `Check the battery health of the laptop before you image it.`
- After: `Do a check of the battery condition of the laptop before you install the image.`

## 4. Sentences

**4.1a — Procedures: imperative, one action per sentence.** Where an instruction chains several actions, break it into a numbered sequence.

- Before: `To rotate the API key, revoke the old key in the dashboard, then, after copying the new key, update API_KEY in .env and restart the service.`
- After: `To rotate the API key, do these steps: 1. Revoke the old key in the dashboard. 2. Copy the new key. 3. Set API_KEY in .env to the new key. 4. Restart the service.`

**4.1b — Descriptions: one subject or one idea per sentence.** Build understanding across a chain of sentences instead of stacking topics into one.

- Before: `The scheduler has two worker pools bound together by a shared queue and connected with retry policies between the ingest service and the archive bucket.`
- After: `The scheduler has two worker pools. A shared queue binds the two pools together. Retry policies connect the pools to the ingest service and to the archive bucket.`

**4.1c — Name the concrete behavior.** Where a relationship varies, say which direction it moves and give real numbers.

- Before: `Different cache sizes will change response latency. No slow queries are permitted.`
- After: `When the cache size increases, the response latency decreases. With a 512 MB cache, the median response latency is 40 ms. Make sure that no query takes longer than 200 ms.`

**4.2a — Keep the subject.** Never delete the noun a sentence is about in order to shorten it, even where a heading appears to supply it.

- Before: `Can be a maximum of 64 characters long.`
- After: `A bucket name can have a maximum of 64 characters.`

**4.2b — Keep the verb.** Do not imply an action with an arrow, a colon, or a bare setting name.

- Before: `Log level to DEBUG.`
- After: `Set the log level to DEBUG.`

**4.2c — Keep the subject of a clause.** Name the thing a condition tests, and the thing a hazard refers back to.

- Before: `If configured, remove the proxy variables. Make sure the container is stopped. If not, this can corrupt the volume.`
- After: `If the proxy variables are configured, remove them. Make sure that the container is stopped. A running container can corrupt the volume.`

**4.2d — Keep the articles.** Repeat the article before each item where its absence would let two nouns read as one thing.

- Before: `Delete the branch and tag.`
- After: `Delete the branch and the tag.`

**4.2e — No contractions.** Write `do not`, `is not`, `cannot` in full.

**4.3a — Lift enumerations into vertical lists.** Where a sentence grows long because it carries many parts, inputs, documents, or actions, move them into a vertical list. A short series inside one sentence is fine.

**4.3b — List mechanics.** Introduce every vertical list with a lead-in sentence ending in a colon. Mark items with one consistent number, letter, dash, or bullet. Start each item with a capital letter. Keep the article in front of the noun that heads each item.

**4.3c — Item punctuation.** No commas or semicolons at the ends of items. Give an item a period only where it is a full sentence; an item can carry a verb inside a relative clause and still be a fragment.

**4.3d — Close the list with a period**, even where every item is an unpunctuated fragment. For how the lead-in and the items are counted against the word limits, see 8.4.

**4.3e — One kind of writing per list.** All instructions or all description. Never mix work steps with statements about what the system does on its own.

- Before: `Backup steps: - Stop the writer process. - The snapshot job copies the volume to S3. - Verify the checksum.`
- After: `The snapshot job copies the volume to S3. To make a backup of the volume, do these steps: 1. Stop the writer process. 2. Make sure that the checksum is correct.`

**4.3f — In safety instructions, repeat the negative command in each item** rather than stating it once in the lead-in. The same shape helps in ordinary lists, but the standard scopes the rule to safety instructions.

- Before: `When you run the migration, do not: - Restart the database. - Scale the deployment.`
- After: `When you run the migration: - Do not restart the database. - Do not scale the deployment.`

**4.3g — Every item continues the lead-in grammatically.** Rework the lead-in, or split a compound item, until each one joins cleanly.

**4.3h — One indentation level.** Where an item has sub-items, fold them into the item as a parenthetical rather than nesting a second list.

**4.4a — Connect related sentences explicitly** with `then`, `thus`, `as a result`, or `at the same time`.

- Before: `The load balancer marks the node unhealthy. The scheduler moves the pods to another node.`
- After: `The load balancer marks the node unhealthy. As a result, the scheduler moves the pods to another node.`

**4.4b — Point back with a demonstrative plus a summarizing noun:** `this method`, `this record`, `this precaution`.

- Before: `Record the current schema version before you run the migration. This helps later.`
- After: `Record the current schema version before you run the migration. This record lets you restore the database to a known state.`

**4.5a — Use articles wherever grammar allows**, and never delete one to shorten the text.

**4.5b — Omit the article for general classes and uncountables.**

- Before: `The compression increases the throughput, and the malformed input can cause the data loss.`
- After: `Compression increases throughput, and malformed input can cause data loss.`

**4.5c — One article for a long series of like items.**

- Before: `Delete the temporary files, the log files, the core dumps, and the stale sockets.`
- After: `Delete the temporary files, log files, core dumps, and stale sockets.`

**4.5d — Article placement sets adjective scope.** One leading article makes the adjective cover every item; a repeated article limits it to the first. Both forms are correct STE, so choose the one that states what you mean and never switch forms without re-checking the meaning.

- All three are new: `Install the new certificate, private key, and CA bundle.`
- Only the certificate is new: `Install the new certificate, the private key, and the CA bundle.`

**4.5e — Drop the article before a noun with an identifier.** The noun plus identifier already works as a proper name.

- Before: `Restart the pod web-7f3a and then check the ticket OPS-1421.`
- After: `Restart pod web-7f3a and then check ticket OPS-1421.`

## 5. Procedural writing

**5.1 — 20 words per sentence, maximum.** Split a long step into two shorter sentences.

- Before: `If the deployment fails, examine the pod events, the container logs, and the readiness probe configuration to find the component that prevented the rollout from completing.`
- After: `If the deployment fails, examine the pod events and the container logs. Then examine the readiness probe configuration to find the cause.`

**5.1a — The cap applies to safety instructions too.** Split a long hazard statement rather than relaxing the limit.

**5.2 — One instruction per sentence and per work step.** The only exception is two actions the reader performs at the same moment.

- Before: `3. Stop the collector service and remove the stale lock file from /var/run.`
- After: `3. Stop the collector service. 4. Remove the stale lock file from /var/run.`

**5.2b — When a step may hold two sentences.** Only where the actions are simultaneous, or where a result or pass criterion follows the action immediately.

- Before: `5. Measure the p99 latency of /health. 6. The latency must not be more than 200 ms.`
- After: `5. Measure the p99 latency of /health. The latency must not be more than 200 ms.`

**5.3 — Every instruction is a direct command.** Never state a work step as a description of what can be done or what gets done.

- Before: `The credentials are to be rotated with the vault CLI, and the container can then be restarted.`
- After: `1. Rotate the credentials with the vault CLI. 2. Restart the container.`

**5.3a — No `must` in front of an imperative.** Reserve `must` for safety instructions and for stating an important condition or requirement.

- Before: `Before you edit nginx.conf, you must stop the daemon.`
- After: `Before you edit nginx.conf, stop the daemon.`

**5.4 — Condition first, then the command,** separated by a comma.

- Before: `Set LOG_LEVEL to debug when the request rate drops below 10 per second.`
- After: `When the request rate drops below 10 per second, set LOG_LEVEL to debug.`

**5.4a — The comma decides the meaning.** Its position controls which verb an adverb attaches to. Read the sentence both ways before you commit.

- `If the agent does not shut down cleanly, kill the process with SIGKILL.`
- `If the agent does not shut down, cleanly kill the process with SIGKILL.` — a different instruction.

**5.5 — Notes carry background only.** Never put an instruction, a requirement, or a limit inside a note.

- Before: `NOTE: The service account must hold roles/storage.admin before the sync starts. 1. Start the sync job.`
- After: `1. Make sure that the service account holds roles/storage.admin. 2. Start the sync job.`

The note carried a requirement, so it becomes a step and no note remains. Do not invent replacement background to keep the note alive.

**5.5a — Notes may run to several sentences,** each capped at 25 words.

**5.5b — No imperatives in notes.** An imperative turns the note into a work step, so move it into the numbered procedure.

**5.5c — A note must never carry damage or injury information.** Promote that content into a proper safety callout, even where the note is phrased without an imperative.

**5.5d — No limits, tolerances, or expected results in a note.** Put them directly after the action they belong to, inside the same work step.

- Before: `B. Run curl -w '%{time_total}' https://api.example.com/health. NOTE: The total time must not be more than 0.2 s.`
- After: `B. Run curl -w '%{time_total}' https://api.example.com/health. The total time must not be more than 0.2 s.`

**5.5e — The note-removal test.** Read the procedure with every note deleted. If the reader could no longer finish the task, a note is carrying load it should not carry — move that information into a work step and repeat the test.

**5.5f — Notes belong in procedures.** In descriptive text, add a note only where an illustration or a table inside that description needs one. Otherwise fold the information into the prose.

## 6. Descriptive writing

**Section 6 preamble (see also rule 4.1) — No imperatives in descriptive text.** Commands belong to procedures; a description reports what the thing is and what it does.

- Before: `The rate limiter tracks requests per API key. Set RATE_LIMIT_RPS to change the ceiling.`
- After: `The rate limiter tracks requests per API key. The RATE_LIMIT_RPS variable sets the ceiling. The Configuration procedure explains how to change it.`

**6.1a — Progressive disclosure.** Start with what the component is and what it is for, then add detail sentence by sentence. Do not compress a description into a few dense sentences.

**6.1b — One subject per sentence.** If a sentence describes two things doing two things, split it.

- Before: `The worker polls the queue and the broker redelivers unacknowledged messages after the visibility timeout expires.`
- After: `The worker polls the queue. The broker redelivers a message if the worker does not acknowledge it before the visibility timeout expires.`

**6.2a — Repeat the key words, in exactly the same wording.** Never swap in a synonym for variety.

- Before: `The scheduler assigns each job to a runner. Once the executor picks up the task, the agent reports progress back to the control plane.`
- After: `The scheduler assigns each job to a runner. The runner then runs the job and reports its progress to the scheduler.`

**6.2b — Signal the relationship** between each sentence and the one before it — addition, contrast, sequence, or result.

**6.3 — 25 words per descriptive sentence, maximum.**

**6.4 — Paragraphs carry the structure** that numbered steps carry in a procedure. A new paragraph tells the reader that a new subject or a different kind of information is starting.

**6.5 — One topic per paragraph, opened by a topic sentence** that names the topic and links back to what came before. Read end to end, the topic sentences should form a usable outline.

**6.6 — Six sentences per paragraph, maximum.** Split at a natural topic boundary.

## 7. Safety instructions

**7.1 — Label the hazard first.** Put an explicit severity label, or its symbol, at the front of every hazard statement, so the reader sees the risk level before the instruction. Never leave a hazard as an unmarked sentence in body text.

**7.1a — Two severity words, by convention.** Use `WARNING` for risk to people and `CAUTION` for risk to equipment, data, or other property. Rule 7.1 asks for "an applicable word" and offers these two as its examples, so other severity words and symbols are permitted where the content still obeys 7.1 through 7.3. Emit the two-level vocabulary unless the document already has a house convention. In aerospace and defense publications the label and its text are conventionally rendered in uppercase; in a Markdown document, render it as a normal callout and keep the two-level vocabulary.

**7.1b — Grade to the real worst case,** not the visible symptom. Where a hazard threatens both people and property, use the higher level.

- Before: `CAUTION: Do not replace the rack PDU while it is energized. You can damage the PDU.`
- After: `WARNING: Do not replace the rack PDU while it is energized. An arc flash can destroy the PDU and cause injury or death.`

**7.1c — Name the concrete failure.** Do not substitute abstract emphasis words such as `essential`, `critical`, or `imperative` for a description of what goes wrong.

- Before: `WARNING: Proper handling of the production database is essential.`
- After: `WARNING: Do not run the reset command against the production database. The command drops every table, and the data is unrecoverable.`

**7.2 — Open with the action.** The first words are the only ones guaranteed to be read; spend them on the imperative, not on background or mechanism.

- Before: `WARNING: Because the request logger serializes the full Authorization header, secrets end up in plaintext log files, so debug logging should not be used in production.`
- After: `WARNING: Do not set LOG_LEVEL=debug in production. The request logger writes the full Authorization header to the log file, which exposes API tokens in plaintext.`

**7.2a — Condition before command.** Do not append the condition to the end of the sentence.

- Before: `CAUTION: Detach the EBS volume only after you stop the container, otherwise the filesystem can be corrupted.`
- After: `CAUTION: Before you detach the EBS volume, stop the container. If the container still has open writes, damage to the filesystem can occur.`

**7.3 — State the consequence after the instruction.** Name the specific failure instead of leaving the risk implied.

- Before: `WARNING: Do not run terraform destroy against the prod workspace.`
- After: `WARNING: Do not run terraform destroy against the prod workspace. This command deletes the RDS instance together with its automated backups. You cannot recover the data.`

## 8. Punctuation and word count

**8.1 — No semicolons.** Write two sentences.

**8.2a–e — Five uses of the hyphen:** a multi-word term acting as a single adjective in front of a noun; a spelled-out two-word number or fraction; a term built from one uppercase letter or a number plus a noun; a verb whose first element is a noun or another part of speech; and a prefix ending in a vowel joined to a root beginning with a vowel.

- Before: `The command accepts a comma separated list. Attach the probe to the 10 pin header. Stress test the cluster, then reenable the webhook.`
- After: `The command accepts a comma-separated list. Attach the probe to the 10-pin header. Stress-test the cluster, then re-enable the webhook.`

**8.2f — Hyphens join, dashes separate.** Use a dash, not a hyphen, for ranges and for a break between ideas.

**8.3a–g — Seven uses of parentheses:** cross-references; illustration callout keys; work-step labels; an abbreviation introduced after its full term; a parenthetical plural ending; a short clarification or limit; and the mirrored alternative case of an otherwise identical instruction, with the alternative terms in the same order. In Markdown, render work-step labels as ordinary numbered-list markers rather than literal `(1)` prefixes.

**8.4 — A colon that introduces a vertical list counts as a full stop.** The lead-in is one sentence; every item is a separate sentence. Each must respect its own limit — 20 words in a procedure, 25 in a description.

**8.5 — Parentheticals are counted twice.** A whole parenthetical counts as one word of the host sentence, and the words inside it count separately as a sentence of their own that must respect the same limit.

**8.6/8.7 — Count as one word:** a number, in digits or spelled out; a number with its unit; an abbreviation, acronym, or initialism, including one attached to a number; an alphanumeric identifier; quoted text, control labels, and formulas; a title, heading, or placard text; the proper name of a person, group, organization, or geopolitical entity; and a hyphenated group of words. Do not count the numbers that label paragraphs or work steps.

- Before (21 words): `Use the method that depends on trial and error only when the log output does not identify the component that failed.`
- After (15 words): `Use the trial-and-error method only when the log output does not identify the failed component.`

## 9. Writing practices

**9.1a — When substitution fails, rebuild the sentence.** Where no approved substitute fits the same part of speech, or where the substitute would change the meaning or produce nonsense, decide what the reader must actually do and express that with approved words in a new structure.

- Before: `The retry count is configurable through the environment.`
- After: `You can set the retry count with an environment variable.`

**9.1b — Check the surrounding text after a rewrite.** Split any sentence that grew too long, delete information that is now given twice, and hoist a repeated instruction into a table heading or a single lead-in line.

**9.3 — No phrasal verbs** whose meaning differs from their parts. Choose a single verb that names the action directly. **Exception:** keep a phrasal verb that appears verbatim in a UI label, a command name, or a flag — rule 1.14a wins.

- Before: `The ingest worker throws away malformed records.`
- After: `The ingest worker discards malformed records.`

**9.4 — Fix one name per item and one wording per type of step,** then reuse them everywhere. Do not vary the phrasing of an instruction that repeats.

**GR-1 — Keep the conjunction `that`** after verbs such as `make sure`, `show`, and `recommend`, even though English allows you to drop it. (`verify` and `confirm` are not approved words — replace them with `make sure` first, then keep the `that`.)

- Before: `Make sure the container is running before you attach the debugger.`
- After: `Make sure that the container is running before you attach the debugger.`

**GR-2a — Re-read any sentence that uses `with`.** It can carry accompaniment, possession, or instrument at once. Where it is carrying a condition, state the condition first in its own clause.

- Before: `Do not restart the broker with replication enabled.`
- After: `When replication is enabled, do not restart the broker.`

**GR-2b — Do not open an instruction with `use` plus a tool name.** Name the action and put the tool in a `with` phrase.

- Before: `Use the migrate CLI to apply the pending schema changes.`
- After: `Apply the pending schema changes with the migrate CLI.`

**GR-3a — Replace an ambiguous pronoun with its noun,** even when the repetition feels clumsy.

- Before: `If you mount the volumes before you start the containers, they can become corrupted.`
- After: `If you mount the volumes before you start the containers, the volumes can become corrupted.`

**GR-3b — Approved pronouns only.** Personal pronouns such as `he` and `she` are unavailable; recast around `you` or around the role.

**GR-4 — Make certain the reader can tell what `this` points to.** Where two things are in reach, restate the item in a new clause.

**GR-5 — Watch for false friends** — words that resemble a word in the reader's first language but mean something else in English.

- Before: `Refer to the actual version of the API reference before you upgrade.`
- After: `Refer to the current version of the API reference before you upgrade.`

**GR-6 — No Latin abbreviations.** Spell out the English equivalent, or drop `e.g.`, `i.e.`, and `etc.` where they add nothing.

**GR-7 — Gender-neutral, non-discriminatory language.**

**GR-8 — Use the apostrophe-s possessive only where it is clearly correct and unambiguous.** When in doubt, rephrase with a modifier or an `of` construction.

- Before: `Update the vendor's SDK to the client's latest release.`
- After: `Update the vendor SDK to the latest client release.`

---

## Word substitutions

For a curated table of common unapproved words and their approved replacements, read `substitutions.md` in this skill's directory. Consult it whenever you need a replacement and apply rule 1.2a: where the replacement changes part of speech, rebuild the sentence rather than swapping the word in place.

## Where STE and /tech-writer disagree

These are intentional divergences, not bugs. Do not "correct" one skill's output with the other.

| Subject | STE (`/ste`) | Google (`/tech-writer`) |
|---|---|---|
| Nouns used as verbs | Banned. `Do a test of the response.` | Fine — strong specific verbs are preferred |
| Sentence length | Hard cap: 20 words procedural, 25 descriptive | Semantic test only: one idea per sentence |
| `-ing` forms | Banned outside a small approved set and technical nouns | Restricted only in chained participial phrases; otherwise allowed |
| Procedure headings | Gerund headings permitted: `## Packaging` | Reader's task: `## Package the release` |
| First person | `we` allowed where the organization is the actor | Use `you`, not `we` |
| Contractions | Expanded in full | Left alone |
| List punctuation | Terminal period after the last fragment | Strictly parallel punctuation across items |
| Phrasal verbs | Replaced with single verbs | Kept — `log in`, `roll back`, `spin up` |
| Imperatives in prose | Banned outside procedures | Fine where it reads naturally |
| Severity labels | `WARNING` and `CAUTION` by convention | Note and Warning callouts; no fixed severity vocabulary |

## Output format

After rewriting, report like this:

```
## STE conversion

### Words (section 1)
- [changes]

### Verbs (section 3)
- [changes]

...one section per rule group where changes were made.

### Sentences over the limit
| Location | Words | Action |
|---|---|---|

### Not converted
- [terms that could not be replaced without changing the meaning, and why]
```

## Source and attribution

The rules above are paraphrased from **ASD-STE100 Simplified Technical English, Issue 9** (January 2025), the standard for technical documentation published by the AeroSpace, Security and Defence Industries Association of Europe. Rule numbers are kept as citation anchors so you can check any paraphrase against the standard itself. Only the bare numbers are ASD's: the standard numbers its rules 1.1–1.14, 2.1–2.2, 3.1–3.7, 4.1–4.5, 5.1–5.5, 6.1–6.6, 7.1–7.3, 8.1–8.7, and 9.1–9.4, plus general recommendations GR-1 to GR-8. The letter suffixes used above (1.2a, 3.6f/g, 8.3a–g, GR-2b, and the rest) are this plugin's own subdivision of a single ASD rule and do not appear in ASD-STE100.

ASD-STE100 is © ASD. This plugin is not affiliated with, endorsed by, or approved by ASD. It does not reproduce the standard's text, and it does not contain the ASD approved-word dictionary. The substitution table is a 122-entry selection of not-approved-word entries and their ASD-assigned alternatives drawn from that dictionary; it cannot tell you whether any other word is approved. For authoritative use, obtain ASD-STE100 from ASD directly.
