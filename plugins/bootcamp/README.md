# bootcamp

> Spin up a swarm of expert subagents to build an interactive **zero-to-hero course site** on any topic — progressive modules, worked examples, hands-on exercises with revealable solutions, checkpoint quizzes, a capstone project, and progress tracking — shipped to `docs/` and **deployed on GitHub Pages**.

## What it does

`/bootcamp <topic>` is built for a **brand-new (greenfield) repo**. It scaffolds the project, orchestrates a swarm of specialist agents to build a complete interactive course, and deploys it live:

- A **curriculum architect** designs the ordered zero→hero learning path — modules, prerequisites, and per-module learning objectives.
- The orchestrator invokes the `frontend-design` skill (`/frontend-design:frontend-design`) to commit to a distinctive aesthetic and build the design system + interaction layer (progress tracking, quizzes, solution reveals, copy-code, a signature interactive element).
- **Content experts** (one per module, in parallel) write deep teaching dossiers — explanations, correct/runnable worked examples, exercises with solutions, common misconceptions, and checkpoint quizzes.
- **Module builders** (one per module, in parallel) turn each dossier into a polished, consistent HTML page.
- A **capstone author** designs an integrative project with a spec, rubric, and reference solution.
- A **QA / proctor** pass drives the real site in a browser via the **Playwright MCP** to verify technical accuracy, links, interactivity, and responsive/mobile layout (if the MCP isn't installed, the skill helps you set it up first).

Then it commits, creates/pushes the repo, **enables GitHub Pages from the `docs/` folder**, polls until the build is green, and reports the live URL.

## A course, not an essay

Where a reference site is written to be *read*, a bootcamp is built to be *worked through*:

- A visible **zero → hero path**, not a pile of articles
- Each module opens with concrete **learning objectives** and ends with a "you can now…" recap
- **Concept → worked example → exercise → solution → checkpoint** rhythm
- **Self-check quizzes** and a **progress tracker** that remembers where you left off
- A **capstone** that proves you can integrate it all

## Output

```
docs/
├── index.html              course home: promise · prerequisites · curriculum map · progress bar
├── 00-orientation.html     setup · mental model · how to use the course
├── 01-<module>.html        objectives → lessons → worked examples → exercises (+solutions)
├── 02-<module>.html          → common mistakes → checkpoint quiz → recap → next
│   …                        (typically 6–10 modules, ramping zero → hero)
├── capstone.html           integrative project: spec · milestones · rubric · reference solution
├── reference.html          cheat sheet · glossary · where to go next
└── assets/
    ├── css/main.css        distinctive design system (built via frontend-design)
    ├── js/main.js          progress tracking · quizzes · solution reveals · signature element
    └── images/ | diagrams/
_course/
├── curriculum.md           the authoritative syllabus
├── design_brief.md         the aesthetic + markup/class contract
├── modules/<slug>.md       per-module teaching dossiers
└── screenshots/            verification artifacts
```

## Usage

```
/bootcamp Rust for programmers coming from Python
/bootcamp Kubernetes from zero to running production workloads
/bootcamp music theory for self-taught guitarists
/bootcamp                          # asks for the topic
```

The skill pins down who "zero" is and what "hero" means before building, so the ramp fits the learner. "Length doesn't matter" — it errs toward **comprehensive**, preferring more well-sequenced modules over padding.

## Requirements

- **`gh` CLI**, authenticated — to create the repo and enable GitHub Pages.
- **Playwright MCP** — the QA/review pass drives the real site in a browser to verify interactivity and mobile layout. If it isn't installed, the skill walks you through adding it before QA:
  ```bash
  # Claude Code
  claude mcp add playwright npx @playwright/mcp@latest
  npx playwright install        # browser binaries
  ```
  ```toml
  # Codex CLI — ~/.codex/config.toml
  [mcp_servers.playwright]
  command = "npx"
  args = ["@playwright/mcp@latest"]
  ```
  (Restart the CLI afterward so the `browser_*` tools connect.) Without it, QA falls back to HTML/structure checks only — the skill says so rather than claiming the site works unverified.

## Interactive by default

A bootcamp is something you *do*, not something you read. Every page is a workspace:

**Core (always built):**
- **Progress tracking & resume** — per-section/module completion in `localStorage`, a real-percentage global progress bar, and "resume where you left off"
- **Progressive-hint solutions** — exercises never spoil by default; a hint ladder (nudge → bigger hint → full solution) lets learners earn the answer
- **Self-check quizzes with real feedback** — multiple choice, true/false, fill-in-the-blank, "predict the output", drag-to-order — each scored, with an *explanation* of why the answer is right
- **Runnable / "try it" demos** — editable, executable code (in-browser runtime or sandbox), or a manipulable model (calculator, parameter sliders, steppable diagram) for non-code topics
- **Copy-code buttons** with copied-state feedback

**Signature element** — one memorable, recurring interaction tuned to the subject: a live REPL, a circuit/physics simulator, an interactive graph explorer, a chord player, a SQL query runner…

**Enhancers (the ones that fit):** spaced-repetition flashcards, hover **glossary tooltips**, table-of-contents **scroll-spy**, **achievements/streaks**, a generated **completion certificate**, per-page **learner notes**, **confidence checks**, light/dark **theme toggle**, and client-side **search + keyboard nav**.

It stays dependency-light (vanilla JS, at most one CDN where a sandbox needs it), works offline-first, is keyboard-operable and ARIA-labeled, and degrades gracefully without JS.

## Mobile-first

Most learners work through a course on their phone, so the build targets mobile as a first-class surface — not an afterthought. The design system is **mobile-first** (single-column ~390px baseline, fluid `clamp()` type, enhanced up with media queries), respects notch/Dynamic-Island **safe areas** (`env(safe-area-inset-*)`), uses fingertip-sized (≥44px) tap targets, and never relies on hover — every interaction works by touch. The QA pass verifies layout and touch interaction on a current iPhone-class viewport (393×852, covering iPhone 15/16/17 Pro) and a small phone, confirming no horizontal scroll and readable text without zoom.

## Deployment

The deliverable is a **live site**. After confirming with you, the skill:

1. Writes a `.gitignore` and commits the course
2. Creates/pushes the GitHub repo (`gh repo create … --push`)
3. Enables GitHub Pages from the `docs/` folder via `gh api`
4. Polls until the build is green
5. Sets the repo's **homepage/website to the Pages URL** (`gh repo edit --homepage …`) so anyone who lands on the repo gets a one-click link to launch the live course, and gives the repo a short description
6. Curls the live URL and reports the link

## Token budget

A full swarm build runs roughly **400K–900K tokens** across all agents, depending on module count and depth. The skill warns before a large run and supports a reduced build (≈5 modules, shorter dossiers, a single QA pass) — without cutting technical accuracy, hands-on exercises, the interactive layer, or deployment.

## Refusals

The skill pushes back and proposes a workable version when a topic is too narrow for a multi-module course, unbounded, or would require harmful capability uplift (it declines the harmful core and offers the legitimate/defensive adjacent course).
