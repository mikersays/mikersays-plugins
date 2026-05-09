---
name: deck
description: Generate a self-contained HTML slide deck from a topic — single file, dark theme, keyboard nav
argument-hint: "[topic]"
allowed-tools: Write, Read, Bash
---

# Deck — Generate an HTML Slide Deck

Produce a single `.html` file the user can double-click to present: scroll-snap slides, dark theme, arrow-key navigation, no external dependencies.

## Process

1. **Get the topic.** Use `$ARGUMENTS` if provided. If empty, ask.
2. **Plan 8–15 slides.** Title slide, content slides (one idea each), closing slide. If the topic is too broad, narrow it and tell the user the angle you picked.
3. **Write the file** with the Write tool to `<topic-slug>.html` in the cwd (lowercase, hyphens — e.g. `intro-to-kubernetes.html`).
4. **Open it.** Try `open` (macOS) or `xdg-open` (Linux). If that fails, print the absolute path so the user can open it themselves.
5. **Report** the path and slide count.

If you don't know the topic well enough to fill 8 slides accurately, say so and ask for source material rather than inventing content. Lorem ipsum and filler defeat the point of the deck.

## File structure

The HTML file has three parts: a `<style>` block (use the template below verbatim), a sequence of `<div class="slide">` elements, and a `<script>` block for keyboard nav. Everything inline — no CDNs, no external CSS or JS — so the file works offline and travels as a single attachment.

### Style template

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DECK TITLE HERE</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  html {
    scroll-snap-type: y mandatory;
    overflow-y: scroll;
    scroll-behavior: smooth;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
    line-height: 1.6;
  }

  .slide {
    width: 100vw;
    height: 100vh;
    scroll-snap-align: start;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 8vh 12vw;
    position: relative;
  }

  .slide-number {
    position: absolute;
    bottom: 2rem;
    right: 3rem;
    font-size: 0.9rem;
    color: #64748b;
  }

  /* Title slide */
  .slide.title { text-align: center; justify-content: center; align-items: center; }

  .slide.title h1 {
    font-size: clamp(2.5rem, 6vw, 5rem);
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(135deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .slide.title p {
    font-size: clamp(1.1rem, 2vw, 1.6rem);
    color: #94a3b8;
    margin-top: 1rem;
  }

  /* Content slides */
  h2 {
    font-size: clamp(1.8rem, 3.5vw, 2.8rem);
    font-weight: 700;
    margin-bottom: 1.5rem;
    color: #f1f5f9;
  }

  p {
    font-size: clamp(1rem, 1.8vw, 1.35rem);
    color: #cbd5e1;
    margin-bottom: 1rem;
    max-width: 52ch;
  }

  ul, ol {
    font-size: clamp(1rem, 1.8vw, 1.35rem);
    color: #cbd5e1;
    margin-left: 1.5rem;
    margin-bottom: 1rem;
  }

  li { margin-bottom: 0.6rem; }
  li::marker { color: #60a5fa; }

  code {
    font-family: "SF Mono", "Fira Code", "Cascadia Code", Menlo, Consolas, monospace;
    background: #1e293b;
    padding: 0.15em 0.4em;
    border-radius: 4px;
    font-size: 0.9em;
    color: #7dd3fc;
  }

  pre {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 1.2rem 1.5rem;
    overflow-x: auto;
    margin-bottom: 1rem;
    max-width: 60ch;
  }

  pre code {
    background: none;
    padding: 0;
    font-size: clamp(0.85rem, 1.4vw, 1.05rem);
    line-height: 1.5;
  }

  strong { color: #f1f5f9; }
  em { color: #a78bfa; font-style: italic; }

  /* Closing slide */
  .slide.closing { text-align: center; align-items: center; }

  .slide.closing h2 {
    font-size: clamp(2rem, 4vw, 3.5rem);
    background: linear-gradient(135deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
</style>
</head>
<body>

<!-- SLIDES GO HERE -->

<script>
document.addEventListener('keydown', (e) => {
  const slides = document.querySelectorAll('.slide');
  const current = Math.round(window.scrollY / window.innerHeight);
  if ((e.key === 'ArrowDown' || e.key === 'ArrowRight' || e.key === ' ') && current < slides.length - 1) {
    e.preventDefault();
    slides[current + 1].scrollIntoView({ behavior: 'smooth' });
  } else if ((e.key === 'ArrowUp' || e.key === 'ArrowLeft') && current > 0) {
    e.preventDefault();
    slides[current - 1].scrollIntoView({ behavior: 'smooth' });
  }
});
</script>
</body>
</html>
```

### Slide examples

Drop these into the `<!-- SLIDES GO HERE -->` slot. The class controls the layout: `title` for the opener, `closing` for the wrap-up, plain `slide` for everything in between.

```html
<div class="slide title">
  <h1>Intro to Kubernetes</h1>
  <p>Container orchestration in 12 slides</p>
  <div class="slide-number">1 / 12</div>
</div>

<div class="slide">
  <h2>Why orchestration?</h2>
  <ul>
    <li>Containers are cheap; managing hundreds of them is not</li>
    <li>You need scheduling, healing, networking, and rollout in one system</li>
    <li>Kubernetes is the de-facto standard — every cloud speaks it</li>
  </ul>
  <div class="slide-number">2 / 12</div>
</div>

<div class="slide closing">
  <h2>Start small. Grow into it.</h2>
  <p>Run <code>minikube start</code> and deploy a single pod before reaching for Helm.</p>
  <div class="slide-number">12 / 12</div>
</div>
```

## Slide content guidance

- One idea per slide. If a slide has more than ~5 bullets or covers two distinct points, split it — dense slides read as walls of text at presentation size.
- Vary the shape. A deck of identical bullet lists is boring; mix in short paragraphs, a code block, a single emphasized sentence. The CSS already styles `<pre><code>`, `<strong>`, and `<em>` for this.
- Keep code blocks under ~12 lines so they fit the viewport without scrolling.
- Number every slide via `<div class="slide-number">N / TOTAL</div>` so the audience can orient themselves.
- Every slide needs a heading (`<h1>` on the title, `<h2>` elsewhere) — that's what makes it feel like a slide rather than a paragraph.
- No `<img>`, no remote fonts, no `<link>`/`<script src>` to anything off-disk. The file should render identically on a plane with no wifi.
