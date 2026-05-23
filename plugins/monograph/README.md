# monograph

> Build a multi-page PhD-level GitHub Pages site on any topic — research, free-licensed photography, a distinctive topic-tuned design, all built by a team of parallel expert subagents and shipped to `docs/`.

## What it does

`/monograph <topic>` orchestrates a team of subagents to produce a long-form scholarly website:

- **Research agent** drafts a 4,000–6,000 word dossier with 30–50 academic-style citations
- **Image research agent** finds and downloads 15–30 Wikimedia Commons / CC-licensed photographs with full attribution
- **Chapter builders** (3–5, in parallel) each produce one 1,200–2,200 word chapter page following a shared design system
- The orchestrator commits to a **distinctive aesthetic chosen for the topic** — typography, palette, layout, and a recurring "signature element" (a live ticking clock, a moving star map, a stopwatch, etc.) that telegraphs the subject at a glance
- A bibliography + per-image-credits page is generated automatically
- The whole site is verified in a headless browser before shipping

## Output

```
docs/
├── index.html             hero · abstract · master chronology · chapter cards
├── <chapter-1>.html       1,200–2,200 words
├── <chapter-2>.html       …
├── <chapter-3>.html
├── <chapter-4>.html
├── references.html        bibliography + image credits
└── assets/
    ├── css/main.css       fresh design system per topic
    ├── js/main.js         signature element + small interactions
    └── images/*.jpg|png   CC-licensed photographs
_research/
├── dossier.md             the source-of-truth research backbone
├── image_manifest.md      per-image attribution and license
├── design_brief.md        the aesthetic decisions, for downstream agents
└── screenshots/           verification artifacts
```

## Usage

```
/monograph the history of Casio watches
/monograph French nouvelle vague cinema, 1958–1968
/monograph the Apollo program, with emphasis on the Lunar Module
/monograph                          # asks for the topic
```

If the topic is broad, the skill will ask one scoping question. If the topic fails the free-licensed-photography test, it will say so and propose adjacent topics.

## Two-topic example

Run on **"the history of Casio watches"**: parchment + ink editorial aesthetic, Fraunces × Newsreader, seven-segment LCD clock in the masthead, 6 pages, 10,500 words, 27 photographs, 50 citations. Live at https://mikersays.github.io/casio-history/

Run on **"the history of psychedelic poster art"** (hypothetical): cream + magenta + cyan maximalist, Recoleta × Druk, rotating San Francisco fog clock as the signature, 5 pages, 9,400 words, 22 photographs.

The two sites should be **indistinguishable from sites made by different design studios**. That is the bar.

## Token budget

A full build costs roughly **500K–800K tokens** across all agents. The skill will tell the user this before starting if it suspects budget pressure. A reduced build (3 chapters, 800-word target, 20 sources, 12 images) is also supported — say so when invoking.

## Shipping

The skill never pushes without asking. When the user says "ship", it:

1. Writes a `.gitignore`
2. Stages `docs/` and `_research/`
3. Commits with a summary message
4. Pushes to `main`
5. Enables GitHub Pages from `main:/docs` via `gh api`
6. Polls until the build is green
7. Curls the live URL and reports

## Refusals

The skill will surface a concern and propose an alternative if asked to write about:

- A living non-public individual (privacy, no free photography)
- Currently litigated material (defamation risk)
- Topics too narrow to fill four chapters
- Topics with zero free-licensed photography available
