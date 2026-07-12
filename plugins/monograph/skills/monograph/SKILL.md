---
name: monograph
description: Build a multi-page PhD-level GitHub Pages site on any topic — long-form scholarly essay, free-licensed photography, a distinctive topic-tuned design, all built by a team of parallel expert subagents and shipped to docs/
argument-hint: "[topic]"
allowed-tools: Write, Read, Edit, Bash, Agent, AskUserQuestion, Glob, Grep, WebSearch, WebFetch, mcp__plugin_playwright_playwright__browser_navigate, mcp__plugin_playwright_playwright__browser_take_screenshot, mcp__plugin_playwright_playwright__browser_resize, mcp__plugin_playwright_playwright__browser_evaluate
---

# Monograph — Build a scholarly GitHub Pages site on a topic

This skill orchestrates a team of parallel subagents to produce a multi-page, PhD-level long-form essay site about a single subject. The output lives in `docs/` so GitHub Pages can serve it directly from the repo's `/docs` folder.

The **design is chosen fresh** for every topic — there is no template aesthetic. Two topics, two sites that look nothing alike.

---

## What you're producing

A 6-page (typical) site:

```
docs/
├── index.html          # hero · abstract · master chronology/table-of-contents · chapter cards
├── <chapter-1>.html    # ~1,200–2,200 words, frontispiece, sub-sections, figures, sidenotes, footnotes
├── <chapter-2>.html    # …
├── <chapter-3>.html
├── <chapter-4>.html    # (chapter count: 3–5 depending on topic depth)
├── references.html     # full bibliography + per-image attribution
└── assets/
    ├── css/main.css    # single cohesive design system — written fresh per topic
    ├── js/main.js      # the signature element + small interactions
    └── images/*.{jpg,png}  # CC-licensed photography only
```

Body essay is **8,000–12,000 words** across all pages. Bibliography is **30–50 sources**. Images: **15–30** Wikimedia Commons / CC-licensed photographs with full attribution.

---

## The team

You are the **orchestrator**. You make the topic-shaping decisions, write the design system, build the index/references pages, and verify the result. You delegate three kinds of work to subagents (via the `Agent` tool, `subagent_type: general-purpose`):

| Agent | Count | Job |
|---|---|---|
| **Research** | 1 | Produce a 4,000–6,000 word source-of-truth dossier with academic-style citations |
| **Image research** | 1 | Find + download CC-licensed photographs from Wikimedia Commons; write a manifest with attribution |
| **Chapter builders** | 3–5 | One per chapter — each receives the design system + relevant research excerpt + image list + strict structural brief |

Spawn the **Research** and **Image** agents in parallel at the start. Spawn the **Chapter builders** in parallel after the design system + index are written.

---

## Process

**If subagent or browser tools are unavailable** (e.g. running under Codex CLI): do the research, image, and chapter work sequentially yourself in the same phase order, ask questions as plain text, and replace Phase 7's browser verification with `grep`-based link/image checks plus curl-ing each page on the local server.

### Phase 0 — Topic intake

Use `$ARGUMENTS` if provided. If empty or vague, ask the user in plain text: "What's the topic?" (AskUserQuestion requires 2–4 concrete options — only use it when you can offer real choices, letting its built-in "Other" cover free-form answers.)

Then ask one follow-up if the topic is broad enough to need scoping — this is a good AskUserQuestion fit, with the scoping angles as options:

- "The history of jazz" → ask: era, instrument focus, geography
- "Coffee" → ask: cultivation, brewing methods, cultural history, third-wave
- "The Apollo program" → narrow enough to proceed

Aim for a topic that admits **a chronological or thematic arc with 3–5 natural chapter divisions** and has **enough free-licensed photography available** to illustrate it. If the topic fails the second test (e.g. "a living politician's 2024 campaign"), say so and propose adjacent topics that pass.

### Phase 1 — Architecture (orchestrator, ~2 min)

Decide:

1. **Chapter count and titles** (3–5). Each chapter should cover a distinct era / theme / dimension. Present the chapter list to the user in your reply before proceeding.
2. **Site slug** — kebab-case, used for the GitHub repo / Pages URL (e.g. `casio-history`, `jazz-1917-1960`, `apollo-program`). If you are inside an existing git repo, use the repo name and skip this step. If `git rev-parse --is-inside-work-tree` fails, run `git init -b main` first.
3. **Working dir** — verify or create `docs/` at the repo root. Create `docs/assets/css/`, `docs/assets/js/`, `docs/assets/images/`, and a top-level `_research/` directory.

### Phase 2 — Parallel research (two subagents, ~5–8 min, run concurrently)

Spawn both in a **single message** with two `Agent` tool calls.

#### Agent A — Research dossier

Brief the agent with **the topic**, **the chapter outline you decided**, and the output path `_research/dossier.md`. Tell it:

- Cover each chapter's territory in a labelled section.
- Use academic-style numbered citations `[N]` inline.
- Bibliography at the end with 30–50 sources. Prefer:
  - Primary sources (corporate / governmental archives, contemporary press)
  - Peer-reviewed journals and well-regarded trade press
  - Wikipedia where it is well-sourced (cite the article, the trade press it cites, or both)
- Be specific: names, dates, places, technical specifications, prices, dimensions, counts.
- Cross-reference disagreements between sources rather than silently resolving them.
- Target 4,000–6,000 words of usable content.
- Use `WebSearch` and `WebFetch` extensively.

#### Agent B — Image research & download

Brief the agent with:

- **Wikimedia Commons is the primary source.** Fall back to other clearly CC-licensed Flickr / institutional archives only if Commons is empty.
- **DO NOT download copyrighted product photos** from corporate sites.
- For each subject, save the original high-resolution image into `docs/assets/images/` as `<kebab-case-subject>.{jpg|png|webp}`.
- Download with `curl -L -A "MonographResearch/1.0 (research)" -o <path> <url>` — Wikimedia 429-rate-limits the default `curl` user agent.
- Write the manifest to `_research/image_manifest.md` with, for each image: filename, what it depicts, source URL, license (CC0/CC BY/CC BY-SA/PD), attribution string ("Photo: NAME / Wikimedia Commons, CC BY-SA 4.0"), resolution.
- Aim for **15–30** successful downloads spanning every chapter. Document the gaps where no free-licensed photo exists; propose stand-ins or a "write around it" plan.

While the subagents work, you can move ahead to Phase 3.

### Phase 3 — Aesthetic commitment (orchestrator, ~3 min)

**This is the most important decision in the project.** Two topics should never look alike. Commit to a bold, topic-appropriate direction before you write any CSS.

Think through these axes, in this order:

1. **Tonal register.** The topic dictates this. Possible registers:
   - **Editorial-archival** (long-form scholarly: history, literary, scientific). Calm, considered, museum-card figures. *Example: Casio watch history → parchment + ink, Fraunces × Newsreader.*
   - **Brutalist-utilitarian** (industrial, infrastructural, technical). Stark contrast, monospace, grid-breaking. *Example: history of nuclear reactors → black/concrete grey, JetBrains Mono + Inter Display.*
   - **Maximalist-baroque** (visual subcultures, fashion, ornament). Layered, ornamented, dense. *Example: the history of psychedelic poster art → cream + magenta + cyan, Recoleta + Druk.*
   - **Cinematic-noir** (crime, espionage, deep time). Dark mode, dramatic light, ultra-wide hero images. *Example: the history of forensic science → near-black + amber, GT Cinetype + IBM Plex Mono.*
   - **Botanical-natural** (nature, materials, agriculture). Warm earth palette, herbarium-card figures, hand-set captions. *Example: the history of tea → bone + sage + ochre, Cormorant Garamond + Söhne.*
   - **Numerical-instrumental** (sport, finance, instruments). Tabular numerals, ticker-style accents, gauge dial figures. *Example: the history of marathon running → off-white + lane-red, Bitter + Roboto Mono.*
   - …and anything else the topic suggests. **Reject "Inter on white".** Reject purple-blue gradient hero. Reject any aesthetic you have produced before in this session.

2. **Signature element.** Pick ONE distinctive, persistent UI element that recurs on every page and that telegraphs the topic in one glance. The Casio site uses a **live ticking seven-segment LCD clock** in the masthead. Equivalents for other topics:
   - Music topic → a live "now playing" mock-spectrum analyzer
   - Astronomy topic → live position of a chosen body (Mars, ISS) in the masthead
   - Cooking topic → a "today's date in the brewing calendar" stamp
   - Cartography → a live mini-map locator that updates per page
   - Sport → a stopwatch / lap counter
   - Cinema → a film-leader countdown digit
   - Architecture → an isometric elevation that rotates per page
   - Make one up if none of these fit. The signature is not optional. It is what makes the site memorable.

3. **Typography pairing.** Distinctive display × refined body × technical mono. **Never Inter / Roboto / Arial on the display.** All of these are on Google Fonts, so the build can actually load them. Cycle through pairings — never reuse one within a session:

   | Display | Body | Mono | Mood |
   |---|---|---|---|
   | Fraunces | Newsreader | JetBrains Mono | editorial warmth |
   | Bricolage Grotesque | Source Serif 4 | Space Mono | confident scholarly |
   | Playfair Display | Cormorant Garamond | IBM Plex Mono | high-contrast academic |
   | Space Grotesk | Work Sans | Fragment Mono | Swiss-modernist |
   | Instrument Serif | Spectral | Share Tech Mono | broadsheet |
   | Anton | Lora | Roboto Mono | magazine-bold |
   | Italiana | EB Garamond | Space Mono | luxury-editorial |
   | DM Serif Display | Crimson Pro | DM Mono | indie-publisher |
   | Unbounded | Manrope | Fira Code | techno-modernist |
   | Old Standard TT | Cardo | VT323 | archival-antiquarian |

   Paid foundry names (GT Sectra, Söhne, Druk, PP Editorial New, Migra, Lyon Text, Berkeley Mono, Bagoss, Recoleta…) are **mood reference only — never declare them in CSS**; the build has no license and they'd silently fall back to system fonts. Load fonts via a Google Fonts `<link>` in each page's `<head>` (with `display=swap`), and declare full fallback stacks in the CSS tokens.

4. **Palette.** Commit to ~5–6 colors: paper, ink, ink-muted, rule, one or two **signal colors** used very sparingly. Avoid 8-color palettes — they read as soup. The signal color must be hot enough to register but rare enough to mean something. Examples that work: cinnabar #b8341c, hunter green #1f6b32, cobalt #1b3a8c, amber #c87b1e, oxblood #8c2310.

5. **Background.** Solid color rarely. Almost always: paper tone + subtle paper-grain SVG noise (15–45% opacity, multiply blend) + faint radial gradients at the corners. Or, for darker themes: a near-black base with a single dim spotlight gradient.

6. **Layout primitives.** Adopt these structural patterns — proven on the Casio build, and topic-agnostic:
   - `.masthead` — sticky top, with mark + nav + signature element
   - `.frontispiece` — chapter title block: roman numeral, era stamp, large headline, deck
   - `.spread` — 2-column grid: `body-col` (≈640px) + `margin` (≈280px for sidenotes). Collapses to one column under ~1080px.
   - `.lcd-strip` (or your topic's equivalent) — full-width divider strip with the signature visual idiom
   - `.figure` — bordered card: image + metadata `<dl>` + italic caption with bold `Plate N` opener
   - `.specsheet` (or `.dossier`, `.gazetteer`, etc.) — bordered technical reference table appropriate to topic
   - `.specimen-grid` — 2- or 3-up image comparison grid
   - `blockquote.tribune` — centered pull quote with large quotation marks
   - `.timeline-row` — year + event + tag, on rules
   - `.sidenote` — margin note with `<span class="label">` header
   - `.footnotes` — numbered scholarly notes block at chapter end
   - `.colophon-foot` — three-column footer with about / chapters / apparatus

7. **Motion.** One well-orchestrated hero entrance (staggered fade) is plenty. Avoid scattered hover micro-interactions. The signature element should have its own life (ticking clock, rotating elevation, pulsing locator). Otherwise restraint.

Write up the chosen direction in a short `_research/design_brief.md` file (~200 words) — palette tokens, font picks, signature element concept, layout primitives. This will be referenced by all chapter builders so they stay coherent.

### Phase 4 — Design system + index (orchestrator, ~10–15 min)

When the research dossier and image manifest are in, write:

1. **`docs/assets/css/main.css`** — a complete design system (500–800 lines is normal). Use CSS custom properties for tokens. Implement every layout primitive listed above. Include a paper-grain SVG noise overlay. Include print styles. **Do not import or copy verbatim from a previous build** — every property is a fresh decision shaped by the design brief.

2. **`docs/assets/js/main.js`** — small vanilla JS (100–200 lines). Implements:
   - The signature element (live updating)
   - `IntersectionObserver` for `.reveal` if you use scroll-triggered fades (avoid on the master chronology — it appears empty in first paint and in screenshots)
   - Footnote popovers on hover (optional)

3. **`docs/index.html`** — the reference page that establishes every pattern. Includes:
   - Sticky `.masthead` with mark + nav + signature element
   - `.hero` with colophon strip, meta line, big `.h-display` headline (with one italicized accent word in the signal color), deck, byline
   - `.lcd-strip`-equivalent divider
   - Abstract / prologue spread with `.lede` drop-cap paragraph and 2–3 sidenotes
   - Master chronology / table of contents (use `.timeline` or whatever the topic suggests — for non-chronological topics, use a thematic index)
   - 3–5 specimen images in a `.specimen-grid` (or topic equivalent), pulled from the image manifest
   - Pull quote — `blockquote.tribune`
   - Chapter cards linking to each chapter page
   - Footnotes block (for any inline `.fn` references on this page)
   - `.colophon-foot` footer

Use the actual sourced photographs in the specimen grid. Cite specific dates / names / figures from the dossier — no placeholder text, ever.

### Phase 5 — Parallel chapter builds (3–5 subagents, ~6–10 min, run concurrently)

For each chapter, spawn one agent with a brief that includes:

1. **Required reading**: have it read `docs/index.html` (the reference page) and `docs/assets/css/main.css` (the design system) and `_research/dossier.md` (the source content) and `_research/design_brief.md` (the design rationale).
2. **Exact output path**: `docs/<chapter-slug>.html`.
3. **Masthead / footer**: copy verbatim from `index.html`, change `<title>`, set `aria-current="page"` on the active nav link.
4. **Page structure**: frontispiece (chapter number, period/scope, `.h-display` with italicized accent, deck) → divider strip → opening spread with `.lede` drop-cap → 4–7 sub-sections each as `<section class="spread">` with body + margin sidenotes → at least one `blockquote class="tribune"` → footnotes block → next-chapter link.
5. **Figures**: assign the specific image filenames from the manifest. Each figure needs `.figure-meta` dl (Ref / Date / Photo / License) and a `<figcaption>` starting with `<b>Plate N</b>`.
6. **Specsheets**: include at least one `.specsheet` per chapter if the topic supports it.
7. **Footnotes**: at least 6 inline `<a class="fn" href="#fn-N" id="fnref-N">N</a>` linking to a `<div class="footnotes">` at the bottom.
8. **Word target**: 1,200–2,200 words of body text.
9. **Voice**: PhD-level scholarly. Specific. Long sentences allowed if earned. No marketing fluff. No "let's explore" / "in this article". Treat the reader as a serious peer.
10. **Use**: wrap every technical designation in `<span class="model-no">…</span>` (or rename to a topic-appropriate class — `<span class="ref">`, `<span class="serial">`). Use `<span class="numeral">…</span>` for tabular figures.

**Send all chapter-builder Agent calls in a single message** with multiple tool_use blocks. They run in parallel.

### Phase 6 — Bibliography + image credits (orchestrator, ~5 min)

Write `docs/references.html`:
- Frontispiece with `§` mark instead of a chapter number
- A **Bibliography** section: ordered list of every source from the dossier in citation order, with linked URLs, formatted as `Author. "Title." Publication, date. URL.` Use `decimal-leading-zero` counters for visual rhythm.
- An **Image Credits** section: one styled "credit card" per image with the thumbnail, filename, depicts, photographer, source URL link, and a license chip. Include a stats line (`Total · N plates · CC BY · N · CC BY-SA · N · …`).
- A **Notes on gaps** sub-section listing subjects for which no free-licensed image was findable.
- A return-to-essay navigation row.

### Phase 7 — Verify + polish (orchestrator, ~3 min)

Start a local server and use Playwright to verify:

```bash
cd docs && python3 -m http.server 4173 > /tmp/monograph-server.log 2>&1 & echo "PID=$!"
```

If port 4173 is already bound, pick another (e.g. 4174) and use it consistently in the navigate URLs below.

For each page:
1. `browser_navigate` to `http://localhost:4173/<page>.html?v=1` (cache-bust)
2. `browser_evaluate`: force-eager all images (`img.loading = 'eager'`) and wait ~2s
3. `browser_evaluate`: verify all images loaded (`naturalWidth > 0`); force-reveal anything with `.reveal` so it shows in screenshots
4. `browser_take_screenshot` with `fullPage: true` to `_research/screenshots/<n>-<page>.jpg`
5. `Read` the screenshot. Visually verify layout, type, image placement.

Common issues:
- **Timeline / list elements appear empty in fresh paint** — caused by `.reveal { opacity: 0 }` waiting for an IntersectionObserver that never fires in a stitched screenshot OR in a user who hasn't scrolled yet. *Fix: strip `.reveal` from any element above the third fold; trust the hero animation as the only motion moment.*
- **Images show as parchment-color placeholders** — `loading="lazy"` not firing. In production this is fine for real users; for screenshot verification, force-eager.
- **Tall pages duplicate content in stitched screenshots** — Playwright artifact on pages over ~15,000px tall. Verify the HTML directly with `grep -c` if you suspect duplication; trust the HTML.

Kill the server when done: `kill <PID>` (the PID echoed at launch), or `pkill -f 'http.server 4173'`.

### Phase 8 — Ship (orchestrator, ~2 min, only if user says so)

Don't push without asking. When the user says "ship" / "push" / "deploy":

1. Write a minimal `.gitignore` excluding `.playwright-mcp/`, `.DS_Store`, etc.
2. Stage `docs/`, `_research/`, `.gitignore` — never `git add -A`.
3. Commit with a HEREDOC message that summarises:
   - Topic
   - Pages, word count, image count, source count
   - Aesthetic direction (one sentence)
   - Co-Authored-By line
4. Verify a remote is set (`git remote get-url origin`). If missing, offer to create the repo: `gh repo create <slug> --public --source=. --remote=origin` (ask public vs private first).
5. Detect the branch — `BRANCH=$(git branch --show-current)` — and `git push -u origin "$BRANCH"`. Never assume `main`.
6. Enable Pages: `gh api -X POST repos/<owner>/<repo>/pages -f "source[branch]=$BRANCH" -f "source[path]=/docs"`. If it returns 409 (Pages already enabled), update instead: `gh api -X PUT repos/<owner>/<repo>/pages -f "source[branch]=$BRANCH" -f "source[path]=/docs"`.
7. Poll `gh api repos/<owner>/<repo>/pages/builds/latest --jq .status` until `built`.
8. Curl the live URL, report HTTP code + the URL.

---

## Quality bar

The site must:

- Render correctly at desktop (1440×900) and mobile (390×844). Test both.
- Pass a 30-second sniff test from a designer: distinctive type, restrained palette, generous whitespace, no "AI slop" patterns (no generic gradients on white, no Inter, no centered card stack, no neon purple).
- Have at least one moment that surprises — the signature element, an unusual layout choice, an unexpected pull quote, an asymmetric figure spread.
- Have **zero placeholder text**. Every word is real, every date is sourced.
- Have working internal links between all pages.
- Cite every fact with a footnote, and every image with full attribution.

## When you should refuse the topic

- **Living non-public individuals.** Privacy concerns and no free-licensed photography.
- **Currently litigated material.** Defamation risk; sources unstable.
- **Topics narrower than 4 chapters can hold.** Suggest a wider framing.
- **Topics with no free-licensed photography available at all.** Suggest commissioning illustrations or picking a different angle.

Surface the concern; propose an adjacent topic that works.

## A note on token budget

A full monograph build costs **roughly 500K–800K tokens** across all agents. The user should know this before you start a build on a tight budget. If they explicitly want a smaller build:

- Reduce to 3 chapters
- Reduce body word target to 800–1200 per chapter
- Reduce bibliography to 20 sources
- Reduce images to 12

But never compromise on: aesthetic distinctiveness, working signature element, real sourced facts, full image attribution.
