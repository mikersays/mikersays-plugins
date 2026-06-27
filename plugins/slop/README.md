# slop

Rewrite any text so it trips every AI-detector tell at once. A parody plugin: it takes the signals people use to spot AI-generated writing — em-dashes, the rule of three, "not X, but Y," relentless positivity, "let's dive in" — and cranks every one of them to the maximum.

Useful for testing AI detectors, teaching people what the tells actually look like, generating cursed examples, or just laughing at the house style of the machines.

## Usage

```
/slop                       # rewrite the text currently in context
/slop path/to/file.md       # rewrite a file in place
/slop "your text here"      # rewrite an inline string
/slop write about coffee    # generate fresh slop on a topic
/slop tier 2 path/to/file   # pin the intensity (1–4, or "max")
```

## Slop tiers — the obnoxiometer

Slop is a dial, not a switch. Pick how unhinged you want it; each tier is a strict superset of the one below.

| Tier | Name | Obnoxiometer | Reads like |
|---|---|---|---|
| **1** | Lightly Seasoned | ~2 | A mid-level manager's slightly-too-polished email — em-dashes and a few inflated words, no emoji, no servility |
| **2** | Corporate Standard | ~5 | A SaaS landing page — every mandatory tell at full density, bold-colon bullets, clean and confident |
| **3** | LinkedIn Thought Leader | ~8 | A post engineered to go viral — emoji, broetry line breaks, "Picture this," servile open and close *(default)* |
| **4** | Singularity | **10000** | A parody built to trip every detector at once — engagement bait, hashtag avalanche, "As an AI language model…" and the whole catalog stacked |

If you don't pick one, the skill offers the tiers (or defaults to Tier 3 when it can't ask) and tells you which it used so you can re-run hotter or cooler. Length limits compose with tiers — slopping to fit a 3,000-char LinkedIn cap keeps the density and trims the length.

## What it does

1. Takes your text (or topic) as input.
2. Asks (or infers) how intense you want it — Tier 1 to Tier 4.
3. Rewrites it to deliberately overuse the AI-writing tells in that tier.
4. Returns the slopped version — same meaning, peak machine smell — and reports the tier plus a tell tally.

It is the evil twin of `tech-writer`: where that plugin removes the tells, this one adds all of them back.

## The tells it weaponizes

- **Punctuation** — em-dashes everywhere, bolded lead-ins with colons, emoji bullets
- **Vocabulary** — delve, tapestry, leverage, robust, realm, navigate, testament, crucial, seamless
- **Rhetoric** — the rule of three, "not just X, but Y," "from A to Z," rhetorical questions answered instantly
- **Structure** — "let's dive in," prompt-restating intros, "in conclusion" wrap-ups, a bullet list for everything
- **Tone** — boundless enthusiasm, "it's important to note," diplomatic both-sidesing, "I hope this helps!"

## Installation

```bash
/plugin install slop@mikersays-plugins
```
