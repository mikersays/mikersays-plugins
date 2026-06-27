# slop

Rewrite any text so it trips every AI-detector tell at once. A parody plugin: it takes the signals people use to spot AI-generated writing — em-dashes, the rule of three, "not X, but Y," relentless positivity, "let's dive in" — and cranks every one of them to the maximum.

Useful for testing AI detectors, teaching people what the tells actually look like, generating cursed examples, or just laughing at the house style of the machines.

## Usage

```
/slop                       # rewrite the text currently in context
/slop path/to/file.md       # rewrite a file in place
/slop "your text here"      # rewrite an inline string
/slop write about coffee    # generate fresh slop on a topic
```

## What it does

1. Takes your text (or topic) as input.
2. Rewrites it to deliberately overuse every catalogued AI-writing tell.
3. Returns the maximally sloppy version — same meaning, peak machine smell.

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
