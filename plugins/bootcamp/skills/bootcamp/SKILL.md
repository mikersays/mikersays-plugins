---
name: bootcamp
description: Spin up a swarm of expert subagents to build an interactive zero-to-hero course site on any topic — progressive modules, worked examples, exercises with solutions, checkpoints, a capstone, and progress tracking — shipped to docs/ and deployed on GitHub Pages. Use when the user says "bootcamp" or "teach me X", asks to build a course, tutorial, training, or learning site, or wants to learn a topic from scratch.
argument-hint: "[topic]"
allowed-tools: Write, Read, Edit, Bash, Agent, Skill, AskUserQuestion, Glob, Grep, WebSearch, WebFetch, mcp__plugin_playwright_playwright__browser_navigate, mcp__plugin_playwright_playwright__browser_take_screenshot, mcp__plugin_playwright_playwright__browser_resize, mcp__plugin_playwright_playwright__browser_evaluate, mcp__plugin_playwright_playwright__browser_click, mcp__plugin_playwright_playwright__browser_type, mcp__plugin_playwright_playwright__browser_press_key, mcp__plugin_playwright_playwright__browser_wait_for, mcp__playwright__browser_navigate, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_resize, mcp__playwright__browser_evaluate, mcp__playwright__browser_click, mcp__playwright__browser_type, mcp__playwright__browser_press_key, mcp__playwright__browser_wait_for
---

# Bootcamp — Build an interactive zero-to-hero course site

This skill is built for **greenfield repos**: it scaffolds the project, builds the whole course into `docs/`, and deploys it on GitHub Pages serving from the `docs/` folder.

You are the **orchestrator / dean**. You shape the curriculum, stand up the design, delegate the heavy lifting to specialist agents in parallel, hold the quality bar, and ship. The phases below are a default scale, not a rigid script — scale the swarm to the topic.

---

## Mental model: how this is different from a reference site

Keep the pedagogy front-of-mind. Every page should answer, for the learner:

- **Where am I on the path?** (zero → hero is a visible, ordered journey, not a pile of articles)
- **What will I be able to do after this?** (each module opens with concrete learning objectives)
- **Show me, then let me try.** (concept → worked example → exercise → solution → checkpoint)
- **Am I actually getting it?** (self-check quizzes, "common mistakes", checkpoints that gate progress)
- **Can I prove it?** (a capstone that integrates everything)

If a page reads like an encyclopedia entry, it has failed. It should read like the best teacher you ever had wrote it.

---

## What you're producing

A multi-page interactive course in `docs/`. Page count scales with the topic — a typical zero-to-hero path is **6–10 modules** plus framing pages:

```
docs/
├── index.html              # the course home: promise, who it's for, prerequisites,
│                           #   the full curriculum map, outcomes, "start here" CTA,
│                           #   overall progress bar
├── 00-orientation.html     # setup / install / mental model / how to use this course
├── 01-<module>.html        # Module 1 — the true beginning (assume zero)
├── 02-<module>.html        # …each module: objectives → lessons → worked examples
├── 03-<module>.html        #   → exercises (+ revealable solutions) → checkpoint quiz
│   …                       #   → "you can now…" recap → next-module link
├── NN-<module>.html        # …final modules reach genuine "hero" depth
├── capstone.html           # an integrative project with a spec, milestones, rubric,
│                           #   and a reference solution (revealable / in <details>)
├── reference.html          # cheat sheet · glossary · "where to go next" · further reading
└── assets/
    ├── css/main.css        # one cohesive design system — built via the frontend-design skill
    ├── js/main.js          # the interaction layer: progress tracking (localStorage),
    │                       #   quizzes, progressive-hint solution reveals, runnable/"try it"
    │                       #   demos, copy-code, and the signature interactive element
    └── images/ | diagrams/ # illustrations, diagrams, screenshots as the topic needs
_course/
├── curriculum.md           # the authoritative syllabus: module list, objectives, ordering
├── design_brief.md         # the committed aesthetic + interaction spec (from you, via
│                           #   the frontend-design skill)
├── modules/<slug>.md       # one content dossier per module (from the content agents)
└── screenshots/            # verification artifacts
```

"Length doesn't matter" — so **err toward comprehensive**. Every module should be substantial enough to actually teach (multiple lessons, several worked examples, 3–8 exercises). Do not pad with fluff; depth means more *real* explanation, examples, and practice, not more words.

---

## The swarm

Delegate via the `Agent` tool. Use `subagent_type: general-purpose` for content/build work; use the dedicated agent types when they fit. Always send sibling agents in a **single message with multiple tool calls** so they run concurrently.

| Agent | Count | Job |
|---|---|---|
| **Curriculum architect** | 1 (subagent) | Designs the zero→hero learning path: module list, ordered prerequisites, per-module learning objectives, what's in/out of scope. Writes `_course/curriculum.md`. |
| **Design system** | you + `frontend-design` skill | Built by **you, the orchestrator**, via the `frontend-design` skill — not delegated (see Phase 2). Produces `docs/assets/css/main.css`, `docs/assets/js/main.js`, and `_course/design_brief.md`. |
| **Content experts** | 1 per module (subagents) | Subject-matter teachers. Each produces a deep teaching dossier for one module: explanations, worked examples (with correct, runnable code/steps), exercises + solutions, common misconceptions, a checkpoint quiz. Writes `_course/modules/<slug>.md`. |
| **Module builders** | 1 per module (subagents) | Front-end engineers. Each turns one content dossier into a polished `docs/NN-<module>.html` page using the shared design system, under the mobile contract below. |
| **Capstone author** | 1 (subagent) | Designs the integrative project: spec, milestones, grading rubric, reference solution. |
| **QA / proctor** | 1–N (subagents) | Verifies: technical accuracy of every code sample/claim, working links/nav, progress + quiz JS, and layout + touch interaction on real mobile viewports via Playwright. |

Run the **curriculum architect first** (everything depends on the module list). Then spawn the **content experts** concurrently and, while they work, build the **design system** yourself via the `frontend-design` skill. Then run the **module builders** concurrently (each needs its dossier + the design system). The capstone and reference pages can build alongside the later modules. QA last.

Scale: a tight build is ~5 modules and a single QA pass; a comprehensive build is 8–10 modules with per-module QA. When the topic is genuinely huge, prefer **more modules over longer modules**.

---

## The mobile contract (non-negotiable, applies to every agent)

Most learners work through a course on a phone. Mobile is a **build constraint for every agent in the swarm**, not a polish pass at the end — and a broken phone layout blocks ship exactly like a wrong code sample does.

**You must propagate these rules three ways:** paste them into every subagent brief that writes CSS, HTML, or JS; restate them as an explicit section of `_course/design_brief.md` so the builder contract carries them; and verify them by observation in Phase 5.

**Every page** (your `index.html`, every module builder's page, capstone, reference):

- Every `<head>` starts with `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`. A page without it is broken on mobile no matter how good the CSS is.
- One column at phone width. Multi-column layouts only above a `min-width` breakpoint — no fixed pixel widths, no markup that assumes a desktop window.
- Long code blocks and wide tables scroll inside their own container (`overflow-x: auto`); they never stretch the page.
- Wide media (diagrams, screenshots, iframes, canvases) capped with `max-width: 100%`.

**CSS (`main.css`):**

- Mobile-first: start from a single-column ~390px layout and enhance up with `min-width` media queries.
- Fluid type via `clamp()` and relative units; body text readable without pinch-zoom.
- Tap targets ≥44×44px, with enough spacing that neighbors aren't mis-hit.
- Honor notch / Dynamic-Island safe areas with `env(safe-area-inset-*)` padding on sticky bars and the footer.
- **Nav-drawer gotcha:** for off-canvas navigation use `html { overflow-x: clip }` — do NOT use `overflow-x: hidden` on `body`, which turns `body` into a scroll container and silently breaks `position: sticky` on every TOC rail and sticky header.

**Interaction (`main.js` and every component):**

- Drive components on `click`/`pointer` events, never on hover. Any hover-revealed UI (glossary tooltips, footnote popovers) is tap-to-toggle on touch.
- Drag-to-order quizzes ship a tap-friendly fallback.
- The **signature interactive element must be fully operable on a phone**. If it genuinely needs width, ship a graceful mobile alternative — never a widget that only half-works below 400px.
- **Scroll-lock gotcha:** when locking scroll for an open drawer, set `document.documentElement.style.overflowY = 'clip'` / `''` — NOT `document.body.style.overflow`, which creates a scroll container with the same sticky-breaking effect as above.

**Content (content experts):** write phone-legible examples — prefer short code lines (~60 chars) over ones that need horizontal scrolling to read, keep tables to a few columns, and avoid wide ASCII-art diagrams that only parse at desktop width.

---

## Process

### Phase 0 — Intake & greenfield scaffold

1. **Topic.** Use `$ARGUMENTS`. If empty/vague, ask the user. Then make it teachable:
   - Pin down the **learner's starting point** ("zero" for whom — total novice? a programmer new to *this*?) and the **destination** ("hero" = can do what, specifically?). One `AskUserQuestion` is usually enough; infer sensible defaults rather than interrogating.
   - Confirm scope is wide enough for a real course but not unbounded. "Learn everything about software" → propose a concrete track. "Learn CSS Grid" → maybe one rich module set rather than 10.
2. **Greenfield setup.** This skill assumes a fresh repo. Check the actual state and adapt:
   - If not inside a git repo, offer to `git init` (and pick a kebab-case project slug for the eventual repo/Pages URL).
   - Scaffold with `mkdir -p docs/assets/{css,js,images} _course/modules _course/screenshots` (note: single-element braces like `{modules}` don't expand in bash — write those paths plain). Don't presume any layout already exists — discover and route to what's there.

### Phase 1 — Curriculum architecture (1 agent)

Spawn the **curriculum architect**. Brief it with the topic, the learner's start/end points, and "comprehensive, length doesn't matter, optimize for genuine zero→hero progression." Have it write `_course/curriculum.md` containing:

- The ordered module list (slug + title), each with a one-line promise.
- Per module: 2–5 concrete **learning objectives** ("By the end you can…"), prerequisites (which earlier modules), and a difficulty rung on the zero→hero ramp.
- An explicit **dependency/ordering rationale** so later agents respect the sequence.
- The capstone concept and what mastery looks like.

Review the returned curriculum yourself and adjust ordering/scope before fan-out. List the modules for the user so they can see the shape before the build fans out.

### Phase 2 — Content (subagents) + design system (you), in parallel

Spawn **in one message** one content expert per module (subagents). While they work, you build the design system yourself.

**Design system — you invoke the `frontend-design` skill.** Use the Skill tool to drive `frontend-design` and produce the course's look and feel. Do this at the orchestrator level — do **not** ask a subagent to call the Skill, since a general-purpose subagent can't be relied on to have the skill in its context. Feed it the topic, the audience, and the interaction requirements from Phase 4. Capture its output as:
- `docs/assets/css/main.css` — a complete, distinctive design system (tokens, typography, color, layout primitives for the course-specific components listed under "Interaction & components"), built **mobile-first to the mobile contract above**. Tell the `frontend-design` skill that a phone is the primary target, not a secondary one: the design has to look intentional at ~390px first and scale up.
- `docs/assets/js/main.js` — implements the full Phase 4 interaction layer (core + signature + enhancers), touch-operable per the mobile contract. It auto-initializes from the DOM so module builders only emit the right markup.
- `_course/design_brief.md` — ~200 words capturing the aesthetic + the exact CSS classes/markup contract module builders must follow, so every page is visually and behaviorally consistent. It must include a **Mobile** section restating the contract in terms of *this* design system: the breakpoints, which components collapse or reflow at phone width, how the nav behaves on a small screen, and the required `<head>` viewport tag.
Aim for an aesthetic that fits the subject and the energy of a bootcamp; **avoid generic AI-template look** (no Inter-on-white, no purple gradient hero). Distinct, confident, legible for long study sessions. If the `frontend-design` skill is not installed, design the system yourself to the same constraints above and still produce all three artifacts, including the `design_brief.md` contract.

**Content experts** (one per module). Brief each with: the topic, the **full curriculum** (so they stay in their lane and reference neighbors correctly), their module's objectives, and the output path `_course/modules/<slug>.md`. Each dossier must contain:
- A plain-language intro that assumes only the stated prerequisites — **never** assume knowledge from a later module.
- Lessons that build one concept at a time, smallest viable steps.
- **Worked examples** with complete, *correct*, runnable code or step-by-steps — verified, not hand-waved.
- **3–8 exercises** of increasing difficulty, each with a hidden **solution** and a short explanation of *why*.
- **Common mistakes / misconceptions** for the module.
- A **checkpoint quiz** (3–6 questions with answers) that gates "you've got this."
- A "you can now…" recap mapping back to the objectives.
- Phone-legible formatting per the mobile contract: short code lines, narrow tables, no wide ASCII diagrams.
Use `WebSearch`/`WebFetch` to get facts, APIs, versions, and best practices right. Accuracy is non-negotiable — a course that teaches wrong things is worse than none.

### Phase 3 — Home page + module builds

Once the design system and dossiers are in:

1. **You build `docs/index.html`** — the course home. It establishes the design language for builders to mirror, and includes: the promise/outcome ("go from zero to hero in X"), who it's for + prerequisites, the **full curriculum map** (ordered, linked, showing the ramp), estimated effort, a global **progress bar** (driven by localStorage), and a clear "Start here" CTA into `00-orientation.html`. Build it to the mobile contract — it is the reference page every builder copies, so a desktop-only home page propagates into the whole course.
2. **Spawn the module builders in parallel** (one message). **Paste the mobile contract into every builder brief** — a subagent that hasn't read this file only knows what you tell it. Each builder must:
   - Read `docs/index.html` (reference), `docs/assets/css/main.css`, `_course/design_brief.md` (the markup/class contract, including its Mobile section), and its own `_course/modules/<slug>.md`.
   - Emit `docs/NN-<module>.html` that renders its dossier in the dossier's order (header → lessons → worked examples → exercises → common mistakes → checkpoint quiz → recap), with revealable solutions (`<details>` or JS toggle per the design contract) and prev/next module nav.
   - Include the `<head>` viewport tag, use only the design system's responsive primitives, and add **no page-local CSS with fixed widths** — if a page needs a layout the design system doesn't have, report it back rather than hand-rolling a desktop-only one.
   - Wire each page into the **progress tracker** (mark-complete control; checkpoint completion updates the global bar) per the JS contract.
   - Use **real, correct content** from the dossier — zero placeholder text, zero "TODO", every code block runnable.
3. Build `capstone.html` and `reference.html` (via the capstone author + a content/build pass), matching the design system and the same mobile contract — these pages carry wide content (rubric tables, cheat-sheet grids, glossary) that most easily breaks on a phone, so give their tables and grids an explicit phone-width reflow or internal scroll.

### Phase 4 — Interaction & components (the bar for "interactive")

The JS (which you build via the `frontend-design` skill in Phase 2, consumed by every module builder) must turn each page into a workspace. Build all of the **core** layer, commit to one **signature** element, then add the **enhancers** that genuinely fit the topic. Don't bolt on widgets for their own sake — every interaction should serve learning (recall, practice, feedback, or motivation). Keep it dependency-light: vanilla JS, and at most a single well-chosen CDN where a sandbox truly needs it; the site must work offline-first and degrade gracefully without JS.

**Core — always build these:**

- **Progress tracking & resume** — per-section and per-module completion persisted in `localStorage`. A global progress bar on the home page, a per-page indicator, and a "resume where you left off" entry point. Track a real percentage, not just visited/unvisited.
- **Revealable solutions with progressive hints** — exercises never spoil by default. Offer a hint ladder (nudge → bigger hint → full solution) so learners earn the answer in steps rather than jumping straight to it.
- **Self-check quizzes with real feedback** — checkpoints use varied item types where they fit: multiple choice, true/false, fill-in-the-blank, "predict the output", and drag-to-order. Give immediate right/wrong feedback *with an explanation* (why the right answer is right), score the checkpoint, and let passing it mark the module complete.
- **Runnable / "try it" code or interactive demos** — for any topic where output can be shown live, make examples editable and runnable in-page (an in-browser runtime, an iframe sandbox for HTML/CSS/JS, or a step-through simulator). For non-code topics, the equivalent is a manipulable model: a calculator, a parameter slider that updates a result, a steppable diagram.
- **Copy-code buttons** on every code block, with copied-state feedback.

**Signature interactive element — pick one, make it excellent:**

The one memorable, recurring interaction that defines the course. It should fit the subject: a live code playground/REPL for a programming language, a circuit/physics simulator, an interactive proof or graph explorer for math, a chord/scale player for music theory, a query runner for SQL, a network/packet visualizer for systems.

**Enhancers — add the ones that fit (aim for several, not all):**

- **Spaced-repetition flashcards** — auto-built from each module's key terms; a review deck on the reference page.
- **Glossary tooltips** — hover/tap any technical term for an inline definition pulled from the glossary.
- **Table-of-contents scroll-spy** — a sticky per-page outline that highlights the current section; smooth-scroll on click.
- **Achievements / streaks** — badges for finishing modules, passing checkpoints, or a daily streak, to sustain motivation across a long course.
- **Completion certificate** — a generated, printable/shareable certificate unlocked when every module + the capstone are done.
- **Learner notes** — a per-page notes box persisted to `localStorage` so learners annotate as they go.
- **Confidence check** — a quick "how solid do you feel?" self-rating per module that feeds the progress view and flags what to revisit.
- **Theme toggle** — light/dark, persisted; important for long study sessions.
- **Search & keyboard nav** — client-side search across modules and prev/next/`/`-to-search keyboard shortcuts.

**Builder contract.** `_course/design_brief.md` must specify the exact markup and class names for each interactive component (the `localStorage` keys, the quiz data attributes, the hint/solution structure, the run-button hook) so every module builder wires the same behavior identically. The JS auto-initializes from the DOM (no per-page bespoke scripting) and is **idempotent and accessible** — keyboard-operable, ARIA-labeled, and safe to re-run.

**Touch parity.** Every interaction in this phase — core, signature, and each enhancer — is built to the **interaction rules of the mobile contract** and is only "done" when it works by tap on a phone. Design each one at phone width first: a quiz whose options are readable and tappable at 393px, a hint ladder whose buttons don't crowd, a notes box that doesn't fight the on-screen keyboard, a theme toggle and search that are reachable from a collapsed nav.

### Phase 5 — QA / proctor pass

QA and review are done by **driving the real site in a browser via the Playwright MCP** (the `browser_navigate`, `browser_resize`, `browser_click`, `browser_type`, `browser_take_screenshot`, `browser_evaluate`, `browser_wait_for`, `browser_press_key` tools). Reading the HTML is not enough — interactivity, layout, and mobile behavior must be *observed*. So Playwright MCP is a hard requirement for this phase, and both you and any QA subagents should reach for it.

**Preflight — make sure Playwright MCP is available.** Before QA, confirm the `browser_*` tools are present. If they are not (the tools aren't listed / calls error that the server is missing), **help the user install it** rather than skipping QA or falling back to HTML-only checks:

- **Claude Code:** add the server, then make sure browsers are installed:
  ```bash
  claude mcp add playwright npx @playwright/mcp@latest
  npx playwright install   # downloads the browser binaries if missing
  ```
  The MCP connects on the next session/restart, so the user may need to restart Claude Code (or reconnect the server) before the `browser_*` tools appear. Tell them this.
- **Codex CLI:** add to `~/.codex/config.toml`, then restart Codex:
  ```toml
  [mcp_servers.playwright]
  command = "npx"
  args = ["@playwright/mcp@latest"]
  ```
- If the user can't or won't install it, say plainly that QA will be **HTML/structure-only** (links, presence of components, code correctness against the dossier) and that interactivity, responsive layout, and the mobile checks below could not be verified.

Once Playwright MCP is confirmed, spawn QA (one agent, or one per module for big builds). It verifies:

1. **Technical accuracy** — re-check every code sample / factual claim against the dossier and reality. Flag anything wrong; fix before shipping. This is the most important check.
2. **Navigation & links** — every prev/next link, the curriculum map, and cross-references resolve.
3. **Interactivity** — start a local server and drive it with Playwright: progress persists across reloads and the bar reflects it, quizzes score and explain, hints ladder up and solutions reveal, runnable/"try it" demos execute, copy buttons work, the signature element works, and every enhancer shipped (flashcards, tooltips, notes, theme toggle, certificate…) actually functions. Also confirm the page is usable with JS disabled (graceful degradation).
4. **Mobile (a ship blocker, checked on every page)** — verify mobile explicitly, not just desktop, and treat a mobile defect exactly like a wrong code sample: fix it, then re-verify at mobile size before shipping.
   - With `browser_resize`, screenshot **every page** at a current iPhone-class viewport (**393×852**, covering iPhone 15/16/17 Pro) as well as desktop (1440×900); spot-check a small phone at 360×780. Sampling one module is not enough — layout breaks page by page.
   - Read every mobile screenshot and confirm the mobile contract holds *as observed*: no sideways scroll, body text readable without pinch-zoom, tap targets not crowded, sticky bars and footer clear of the safe area, code blocks and tables scrolling internally instead of stretching the page, nothing clipped off the right edge, images loaded, no empty-on-first-paint sections.
   - Confirm every page has the `<head>` viewport tag: `browser_evaluate` → `!!document.querySelector('meta[name=viewport]')`.
   - **Drive the interactions at 393×852**, don't just look at them: open and close the nav drawer (and confirm sticky headers/TOC still stick afterward), answer a quiz, ladder through a hint to a solution, run a "try it" demo, tap a glossary tooltip, and operate the **signature element** by tap. Anything that needs hover to work is a defect.
   - **Horizontal-scroll check:** `scrollWidth > clientWidth` on `html` is a **false positive** when an off-canvas nav drawer sits off-screen under `overflow-x: clip` — the drawer inflates `scrollWidth` even though the user can't scroll. Verify actual scrollability instead: `const before = html.scrollLeft; html.scrollLeft = 200; const canScroll = html.scrollLeft > 0; html.scrollLeft = before;` — flag only if `canScroll` is true.
   - Fix mobile defects in the **shared CSS/JS** where the cause is systemic, so the fix lands on every page at once; only patch a single page when the problem is genuinely local to it. After any such fix, re-screenshot the affected pages at mobile size — a shared-CSS change can regress pages you already passed.

```bash
cd docs && python3 -m http.server 4173 > /tmp/bootcamp-server.log 2>&1 &
# …navigate http://localhost:4173/<page>.html?v=1, force-eager images,
#   screenshot to _course/screenshots/<n>-<page>.jpg, Read it back …
# kill the server when done
```

Fix issues, re-verify the ones you touched. Don't claim it works without having observed it working.

### Phase 6 — Ship & deploy GitHub Pages

The deliverable includes a **live, deployed site**. Inspect the repository before asking any deployment question:

- **Existing remote:** proceed with commit, push, and GitHub Pages deployment without asking whether the repository should be public. Preserve the repository's current visibility. In particular, if it is private, assume the user's GitHub plan supports private-repository Pages and deploy to that private repository directly.
- **No remote:** creating a GitHub repository is a new outward-facing resource, so ask for approval before creating it. State that the proposed default is a public repository, but do not ask this question when a remote already exists.

Then:

1. Write a minimal `.gitignore` (`.playwright-mcp/`, `.DS_Store`, server logs, etc.).
2. Stage `docs/`, `_course/`, `.gitignore` — never blind `git add -A` if the repo has unrelated files; here, on greenfield, staging the course tree is fine.
3. Commit with a HEREDOC message summarizing: topic, module count, what the learner can do at the end, the aesthetic in one line. End with your harness's standard co-author attribution line, if any.
4. **Project-instructions files — do this before pushing to the remote.** Run the `/init` skill to generate a `CLAUDE.md` that documents the course repo (its structure, the `docs/` + `_course/` layout, how to serve and deploy it) so the next agent to open the repo has orientation. If the `/init` skill is unavailable (e.g. Codex CLI), write the `CLAUDE.md` by hand covering the same points. Then create a minimal `AGENTS.md` next to it whose **only** content is an instruction to read `CLAUDE.md` — so Codex CLI agents get pointed at the same context:
   ```markdown
   # AGENTS.md

   Read CLAUDE.md.
   ```
   Stage and commit both files (amend the previous commit or add a small follow-up commit) so they land in the same push.
5. **Remote.**
   - If no remote exists: with the user's approval, create one with `gh repo create <slug> --public --source=. --remote=origin --push` (or have them create it).
   - If a remote already exists: do not ask about creating a public repository or changing visibility. Run `git push -u origin <branch>` and **respect its current visibility**.
   - If the existing repository is private (`gh repo view --json visibility -q .visibility` returns `PRIVATE`), keep it private and continue directly to GitHub Pages setup. Never offer to make it public and never run `gh repo edit --visibility public`. Assume private Pages is available; only report a plan/billing limitation if the GitHub API actually rejects Pages setup for that reason.
6. **Enable Pages from the `docs/` folder on the branch** (this is the explicit ask). Resolve `<branch>` from the repo (`git branch --show-current`) rather than assuming `main` vs `master`, and `<owner>/<repo>` from `gh repo view --json nameWithOwner -q .nameWithOwner`:
   ```bash
   gh api -X POST repos/<owner>/<repo>/pages \
     -f "source[branch]=<branch>" -f "source[path]=/docs"
   ```
   (If Pages is already configured, `PUT` the same endpoint to update the source.)
7. Poll until built and capture the live URL:
   ```bash
   gh api repos/<owner>/<repo>/pages/builds/latest --jq .status   # until "built"
   ```
   The Pages URL is typically `https://<owner>.github.io/<repo>/` — confirm the exact value from `gh api repos/<owner>/<repo>/pages --jq .html_url`.
8. **Always add the GitHub Pages site URL to the repository About section's Website field** by setting the repo homepage to the exact Pages `html_url` captured above, so anyone who finds the repo gets a one-click link to launch the live course. Also give the repo a short, useful description:
   ```bash
   gh repo edit <owner>/<repo> \
     --homepage "https://<owner>.github.io/<repo>/" \
     --description "<one-line: what this course teaches, zero→hero> — live: https://<owner>.github.io/<repo>/"
   ```
9. Curl the URL, report the HTTP status and the link.

---

## Quality bar

The course must:

- **Actually teach zero→hero.** A motivated beginner who works through it end to end reaches the stated destination. Test the ramp: no module assumes anything not taught earlier.
- **Be correct.** Every code sample runs; every claim is right. Verified, not asserted.
- **Be interactive.** The full Phase 4 core layer works, plus a real signature element and the enhancers that fit.
- **Be hands-on.** Every module has exercises with solutions. Practice, not just prose.
- **Look distinctive and stay readable** for long sessions — designed via the `frontend-design` skill, not a generic template.
- **Work on a phone.** Every page and interaction meets the mobile contract, observed on the Phase 5 viewports. If mobile couldn't be verified (no Playwright MCP), say so explicitly instead of claiming it works.
- **Have zero placeholders.** No "TODO", no "coming soon", no lorem ipsum.
- **Be deployed.** Live on GitHub Pages from `docs/`, URL reported.

## When to push back on a topic

- **Too narrow** for a multi-module course → propose a single rich module set or a broader framing.
- **Unbounded** ("learn all of math") → propose a concrete, sequenced track and name what's out of scope.
- **Requires harmful capability uplift** (e.g. weaponization, real intrusion against third parties) → decline the harmful core; offer the legitimate/defensive adjacent course.

Surface the concern and propose the version that works, rather than silently doing something smaller.
