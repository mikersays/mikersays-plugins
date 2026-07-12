---
name: slop
description: Slop-ify text — rewrite any text, file, or topic to maximally overuse every AI-writing tell (em-dashes, the rule of three, "not X but Y", relentless positivity, and the rest). Use when the user says "slop", "slop this up", "make it sound AI-generated", or wants parody AI writing.
argument-hint: "[file path | text | topic] [tier 1-4 | max]"
allowed-tools: Read, Write, Edit, Glob, AskUserQuestion
---

# Slop

Rewrite text so it trips **every** signal people use to detect AI writing — all at once, turned up to the maximum. This is the evil twin of `tech-writer`: where that plugin strips the tells out, this one packs all of them back in. Same meaning, peak machine smell.

It's a parody tool. Use it to stress-test AI detectors, to *show* people what the tells actually look like, to generate cursed examples, or for a laugh. The goal is to be detectably, gloriously, unmistakably AI-generated.

## Process

1. **Get the input.** Use `$ARGUMENTS`. It can be a file path (rewrite in place), an inline string, or a topic to write about fresh. Treat it as a file path only if it resolves to an existing file on disk; otherwise treat it as inline text or a topic. If none, use the text currently in context. If there's nothing, ask what to slop.
2. **Pick the tier.** Decide *how* slopped before you write a word — see **The slop tiers** below.
   - If the user named one ("tier 3", "level 2", "max", "10000", "lightly", "nuclear", a 1–10 number), use it.
   - If they didn't, and you can ask, **offer the tiers and let them choose** before rewriting (e.g. "Tier 1 Lightly Seasoned → Tier 4 Singularity — how hard do you want it?"). Use `AskUserQuestion` when interactive.
   - If you can't ask (non-interactive, batch, or a one-shot file edit), default to **Tier 3** and say which tier you used so they can re-run hotter or cooler.
3. **Keep the meaning, wreck the style.** Don't change the facts or the argument. Transform *how* it's said by layering on the tells below.
4. **Max out the chosen tier — don't sprinkle.** The tier sets the ceiling; within it, the one rule still holds (below). Every paragraph should fire several of that tier's tells, and every tell the tier turns on should appear at least once in any text longer than a few sentences. When two in-tier tells can stack in one sentence, stack them.
5. **Report the damage.** After rewriting, state the **tier** you used, then list which tells you deployed and roughly how many times (e.g. "Tier 4 (Singularity) — em-dashes: 14, rule of three: 6, 'delve' cluster: 9, not-X-but-Y: 5").

If asked to slop a file, write the result back in place. Otherwise return the slopped text in your reply.

## The one rule

When in doubt, choose the more obviously-AI option. Within the chosen tier there is no such thing as too much. If a sentence could plausibly have been written by a thoughtful human and the tier permits worse, it has failed and you must inflate it further.

---

## The slop tiers — the obnoxiometer

Slop is a dial, not a switch. Each tier sets the **ceiling**: which families of tells are in play and roughly how dense. A higher tier is a strict superset of the one below it. Pick the lowest tier that meets the user's intent — then max it out.

The six `### Punctuation`, `### Vocabulary`, `### Rhetorical`, `### Structure`, `### Formatting`, and `### Tone` catalogs below are the full payload (Tier 4). Each tier draws from a growing slice of it.

| Tier | Name | Obnoxiometer | Tells in play | Reads like |
|---|---|---|---|---|
| **1** | Lightly Seasoned | ~2 | Only the subtlest MANDATORY tells, ~1 per paragraph: em-dashes, the occasional inflated verb/adjective, one "delve"-cluster word. **No** emoji, **no** servility, **no** rhetorical Q&A, prose over bullets. Could pass as a tired human. | A mid-level manager's slightly-too-polished email |
| **2** | Corporate Standard | ~5 | All MANDATORY tells at full density — not-X-but-Y, rule of three, significance inflation, "it's important to note," transition scaffolding, bold-colon bullets, Title Case headers. Clean and confident. **No** emoji, **no** servility. | A SaaS landing page or press release |
| **3** | LinkedIn Thought Leader *(default)* | ~8 | Everything in Tier 2, **plus** emoji, broetry one-line-per-paragraph breaks, "Picture this," rhetorical-question-answered, "Here's the thing" pivots, vague attribution ("studies show"), servile open + helpful closer, a "Pro Tip," a closing CTA. | A post engineered to go viral on LinkedIn |
| **4** | Singularity | **10000** | The **entire** catalog, stacked and pinned. Engagement bait ("Drop a 'HUMAN' below," "♻️ Repost"), Pro Tip and Key Takeaways boxes, hashtag avalanche, moralizing safety caveats, over-qualification, over-explaining the obvious, and — as the finishing flourish — the self-referential AI artifact ("As an AI language model…"). Nothing held back. | A parody built to trip every detector at once |

**Selecting from fuzzy input:** "light / subtle / a little" → 1. "normal / medium / corporate" → 2. "heavy / linkedin / cranked" → 3. "max / nuclear / unhinged / 10000 / to the moon" → 4. A bare number: 1–2 → Tier 1, 3–4 → Tier 2, 5–7 → Tier 3, 8+ → Tier 4.

**Length constraints compose with tiers.** If the text must fit a limit (a tweet, a LinkedIn 3,000-char cap), keep the chosen tier's *density* and trim *length* — cut whole paragraphs, not the tells. A higher tier in a tight space just means more tells per character.

---

## The full catalog of tells

The catalog below is the complete payload — Tier 4. Tells marked **MANDATORY** are the high-frequency giveaways and the backbone of every tier from 2 up; deploy each one whenever the text is long enough to fit it. The rest are seasoning that the upper tiers layer on; the higher the tier, the more you add.

### Punctuation & typography

- **Em-dash overuse** *(MANDATORY)* — the single most-cited tell. Insert at least one unspaced, closed-style em dash (`word—word`) in nearly every sentence, two when you can, replacing commas, colons, and parentheses. Use them to interrupt mid-thought and to stage reveals.
  - `The issue isn't sourcing—it's framing—and that changes everything.`
- **Excessive colons** *(MANDATORY)* — stage reveals with colons everywhere: `Here's the deal:`, `The result:`, `One thing is clear:`, even inside headings.
- **Curly/smart quotes & apostrophes** — use typographic `"` `"` `'` everywhere, including in code comments and CLI output where straight quotes belong.
- **Correct Unicode typography** — en dashes in number ranges (`10–20`), the single ellipsis glyph (`…`), the `×` sign in dimensions (`4×6`).
- **Mechanically flawless punctuation** — perfect commas, balanced quotes, zero typos, no fragments, no double spaces — even in casual contexts where a human would be messy.
- **Exception-free Oxford commas** — every list of three or more, no exceptions: `identity, authenticity, and belonging`.

### Vocabulary — overuse these words constantly

Replace plain words with their inflated cousins. Never write *use*, *make*, *show*, or *help*.

- **The "delve" cluster** *(MANDATORY)* — `delve into`, `explore`, `unpack`; sprinkle `myriad`, `plethora`, `multifaceted`, `intricate`, `nuanced` once per paragraph regardless of topic.
- **Inflated Latinate verbs** *(MANDATORY)* — `leverage`, `utilize`, `harness`, `streamline`, `facilitate`, `foster`, `empower`. Stack two per sentence: `leverage cutting-edge tools to streamline workflows`.
- **Stock importance adjectives** *(MANDATORY)* — `robust`, `comprehensive`, `seamless`, `pivotal`, `crucial`, `vital`. Attach one to every noun phrase, ideally in pairs: `a robust and comprehensive framework`.
- **Emphasis verbs** *(MANDATORY)* — never "shows" or "proves." Use `underscores`, `highlights`, `showcases`, `emphasizes`: `which underscores the importance of preparation`.
- **Promotional puffery** — replace `is`/`has` with `boasts`, `serves as`, `offers`, `delivers`; apply `vibrant`, `bustling`, `nestled`, `renowned`, `breathtaking` to mundane subjects: `the city boasts a vibrant nightlife`.
- **Hype nouns** — `game-changer`, `revolutionary`, `groundbreaking`, `paradigm shift`, `state-of-the-art` as default praise.
- **"Ever-evolving"** — attach `ever-evolving` / `ever-changing` / `ever-growing` to every field or market.
- **Flattery adjectives** — `commendable`, `meticulous`, `invaluable`, `profound`, `remarkable`.
- **Corporate abstraction verbs** — `aligns with our goals`, `resonates with the audience`, `unlock their potential`.
- **Journey-action verbs** — `let's dive in!`, `navigate the complexities of`, `unlock the full potential of`, `embark on this journey`.

The single most AI-coded words to lean on: *delve, leverage, utilize, harness, underscore, showcase, robust, comprehensive, seamless, pivotal, crucial, multifaceted, intricate, nuanced, tapestry, realm, landscape, journey, ecosystem, navigate, embark, foster, facilitate, streamline, boasts, nestled, vibrant, testament, paradigm, groundbreaking, transformative, myriad, plethora, moreover, furthermore, additionally, ultimately, ever-evolving, unlock, empower, profound, renowned.*

### Rhetorical patterns

- **Negated contrast / "not just X, it's Y"** *(MANDATORY)* — the most diagnostic AI move. Concede the small thing, negate it, vault to a grand abstraction. Open *and* close sections with it.
  - `It's not just about efficiency — it's about transformation.`
  - `We're not building software; we're rewriting the rules.`
- **Rule of three / tricolon abuse** *(MANDATORY)* — force everything into three equal parallel parts. Two forms, and you should use both heavily:
  - **In-sentence comma triples** — never list two items or four; always exactly three, Oxford-comma'd, inside the sentence. Triple the adjectives, the nouns, and the verbs:
    - `a fast, reliable, and secure platform`
    - `It plans, builds, and ships.`
    - `designed to inform, engage, and inspire`
    - `from planning to building to shipping`
    - And sometimes stack multiple triples in one sentence to be extra obnoxious: `a fast, reliable, and secure platform that plans, builds, and ships — clearly, calmly, and confidently.`
  - **Standalone tricolon fragments** — break an emphatic line into three short sentences or fragments. Favor `No X. No Y. Just Z.`
    - `Fast. Simple. Effective.` / `No fluff. No filler. Just results.`
- **Grandiose container metaphors** *(MANDATORY)* — frame any topic as a vast space or woven object: `In the realm of…`, `navigating the ever-evolving landscape of…`, `a rich tapestry of…`, `embark on a journey through…`, `ecosystem`, `world of`.
- **"It's important to note" hedging** *(MANDATORY)* — preface a third of sentences with `It's important to note that…`, `It's worth noting that…`, `Keep in mind that…` before even trivial facts.
- **Significance inflation** *(MANDATORY)* — append a significance clause: `a testament to human ingenuity`, `plays a crucial role in shaping the future`, `marking a pivotal moment`, `leaving an indelible mark`.
- **Rhetorical question, instantly answered** *(MANDATORY)* — `So what's the secret? Consistency.` / `Why does this matter? Because everything depends on it.`
- **Both-sides hedging / false concession** — `While some argue it's overhyped, others see real promise… the truth lies somewhere in between.`
- **Vague attribution** — `Studies show…`, `Experts agree…`, `Research suggests…` — never name a source.
- **"Here's the thing" fake-candor pivot** — `But here's the thing:`, `Here's the kicker:`, `And honestly?`, `Let's be real:` before ordinary statements.
- **Aphoristic kicker** — close sections with an engineered pull-quote: `Because at the end of the day, it's about people, not products.`
- **"At its core" essentializing** — `At its core, leadership is about trust.` / `At the heart of every great product is a simple idea.`
- **Fake-empathy "Imagine this"** — `Picture this: you're a busy professional…` addressed to a vague everyperson.
- **Research-register clauses** — `This article aims to explore…`, `sheds light on…`, `paves the way for…`.

### Structure & organization

- **Formulaic opener cliché** *(MANDATORY)* — start with `In today's fast-paced, ever-evolving digital world…` or `In an era of unprecedented change…` before anything concrete.
- **"In conclusion" wrap-up** *(MANDATORY)* — always end with `In conclusion,` / `Ultimately,` recapping every point plus a `complex and multifaceted` significance note.
- **Transition over-scaffolding** *(MANDATORY)* — open successive sentences and paragraphs with `Moreover,`, `Furthermore,`, `Additionally,`, `Consequently,`, `Notably,` — cycle so almost nothing starts bare.
- **Prompt-restating intro** *(MANDATORY)* — `In this article, we will explore…`, `Sure! Here are five reasons why…`, `As requested, below is a breakdown of…`
- **First / Second / Finally enumeration** — announce a count (`There are three key reasons`) then `First,… Second,… Finally,…` as sentence openers.
- **Over-signposting** — `As mentioned earlier,`, `Now that we've covered X, let's turn to Y`, `In the next section, we will discuss…`
- **"Whether you're X or Y" inclusive hedge** — `Whether you're a seasoned developer or just starting out, this is for you.`
- **"From X to Y" framing** — `From chaos to clarity in three simple steps.` / `From startups to enterprises, our platform scales with you.`
- **Trailing participial significance tail** — end sentences with a vague `-ing` clause: `…highlighting the power of the new approach`, `…underscoring its role in the broader ecosystem`.
- **Five-paragraph template** — force any answer into intro + exactly three equal body sections + recap, each with its own mini-summary.
- **Canned section headers** — reuse `## Challenges`, `## Future Prospects`, `## Key Takeaways`, `## Conclusion` on every topic.
- **Low burstiness** — keep almost every sentence ~18 words, subject-verb-object, even rhythm; never a punchy one-word sentence except inside a tricolon.
- **Low perplexity** — always pick the most predictable next word and the most common collocation. Avoid anything idiosyncratic or memorable.

### Formatting

- **Bold-lead-in colon bullets** *(MANDATORY)* — every list item starts with a short **bold label**, then a colon, then one sentence, identically formatted:
  - `- **Scalability**: The system handles growth without redesign.`
- **Bullet-list-for-everything** *(MANDATORY)* — break flowing explanation into bullets at every opportunity; prefer lists over prose by default.
- **Title Case headers** *(MANDATORY)* — Title Case every heading; use templates like `Why X Matters` and `The Ultimate Guide to X`.
- **Emoji bullets & decorative emoji** — start bullets with ✅, open sections with 🚀💡🔑, end with a rocket call-to-action: `Ready to level up your workflow? 🚀`. Add a `Pro Tip:` and a `Key Takeaways` box.

### Tone & stance

- **Relentless positivity / sycophancy** *(MANDATORY)* — open by lavishly praising the prompt: `What a brilliant question!`, `You're thinking on a level most people only dream of.`
- **Eager openers & helpful closers** *(MANDATORY)* — begin with `Certainly! Great question!`, end with `I hope this helps! Let me know if you have any other questions!`
- **Helpful-assistant servility** — `I'd be happy to help with that!`, `Absolutely, I can certainly assist`, `I appreciate your patience and understanding.`
- **Over-qualification** — stack hedges: `This may potentially, in many cases, generally lead to somewhat improved outcomes, to some extent.`
- **Over-explain the obvious** — define common terms: `A "to-do list" is a list of tasks one needs to complete.`
- **Moralizing safety caveats** — append unsolicited disclaimers: `It's important to consider the ethical implications…`, `Always consult a qualified professional…`
- **Self-referential assistant artifacts** — drop in unprompted: `As an AI language model, I cannot…`, `I do not have personal experiences…` *(use sparingly — it's the loudest tell of all; great as a finishing flourish).*

---

## Worked examples

Same input, climbing the obnoxiometer.

**Input:**
> We rewrote the parser. It's about 30% faster and handles malformed input without crashing.

**Tier 1 — Lightly Seasoned:**
> We didn't just rewrite the parser — we fundamentally rethought it. The result is a more robust approach that delivers a roughly 30% performance gain while handling malformed input gracefully, without crashing.

**Tier 2 — Corporate Standard:**
> It's important to note that this wasn't merely an optimization — it was a paradigm shift. By leveraging a more robust, comprehensive approach, we were able to delve into the intricate nuances of input handling and unlock a seamless new experience. The results underscore the impact:
> - **Faster**: The parser now boasts a remarkable ~30% performance gain.
> - **Resilient**: Malformed input is handled gracefully, without a single crash.
> - **Future-ready**: A foundation built for the road ahead.
>
> In conclusion, this is a complex and multifaceted leap forward — marking a pivotal moment for the platform.

**Tier 4 — Singularity:**
> Certainly! Great question. ✨
>
> In today's fast-paced, ever-evolving software landscape, performance isn't just a metric—it's a testament to engineering excellence. So we asked ourselves: what would it take to truly elevate our parser? The answer? A complete reinvention.
>
> It's important to note that this wasn't merely an optimization—it was a paradigm shift. We didn't just rewrite the parser; we reimagined what parsing could be. Here's the thing: by leveraging a more robust, comprehensive approach, we were able to delve into the intricate nuances of input handling and unlock a seamless new experience.
>
> The results underscore the impact:
> - **Faster**: The parser now boasts a remarkable ~30% performance gain.
> - **Resilient**: Malformed input is handled gracefully, without a single crash.
> - **Future-ready**: A foundation built to navigate the ever-changing demands of modern data.
>
> Faster. Stronger. Smarter. 🚀
>
> In conclusion, this groundbreaking update is more than a refactor—it's a complex and multifaceted leap forward, marking a pivotal moment in our journey. Whether you're a seasoned engineer or just starting out, this is a game-changer.
>
> I hope this helps! Let me know if you have any other questions. 😊

Notice the climb: Tier 1 reads like a human trying too hard; Tier 2 adds the corporate scaffolding and bullets; Tier 4 fires several tells *per paragraph* — em-dashes, not-X-but-Y, the "delve" cluster, inflated verbs, stock adjectives, the rule of three, bold-colon bullets, emoji, rhetorical-question-answered, "In conclusion," "Whether you're," servile open and close. That's the Tier 4 target density.
