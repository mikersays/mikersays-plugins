---
name: deck
description: Generate an HTML slide deck from a topic
argument-hint: "[topic]"
allowed-tools: Write, Read, Bash
---

# Deck — Generate an HTML Slide Deck

Generate a self-contained HTML slide deck from a topic. Zero dependencies — pure HTML, CSS, and minimal JS in a single file.

## Process

1. **Get the topic.** If the user provided text via `$ARGUMENTS`, use that as the topic. If `$ARGUMENTS` is empty, ask the user what the deck should be about.

2. **Plan the outline.** Create 8–15 slides with this structure:
   - **Slide 1:** Title slide — topic name, optional subtitle
   - **Slides 2–N:** Content slides covering key points, one idea per slide
   - **Last slide:** Summary or closing takeaway

3. **Write the HTML file** using the Write tool. Save it as `<topic-slug>.html` in the current working directory (lowercase, hyphens, no spaces — e.g., `intro-to-kubernetes.html`).

4. **Open the file** in the user's default browser:
   - macOS: `open <file>`
   - Linux: `xdg-open <file>`
   - If the open command fails, tell the user the file path so they can open it manually.

5. **Report** the file path and slide count to the user.

## HTML Template

The generated HTML file MUST follow this structure exactly. Do not use external stylesheets, scripts, or CDN links.

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
  .slide.title {
    text-align: center;
    justify-content: center;
    align-items: center;
  }

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

  li {
    margin-bottom: 0.6rem;
  }

  li::marker {
    color: #60a5fa;
  }

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
  .slide.closing {
    text-align: center;
    align-items: center;
  }

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

Each slide is a `<div class="slide">` with a `<div class="slide-number">` at the bottom. The title slide gets class `slide title`, the closing slide gets class `slide closing`, and content slides get just `slide`.

## Slide Content Rules

- **Every slide MUST have a heading** (`<h1>` for title, `<h2>` for content).
- **3–5 bullet points maximum per slide.** If you have more, split into two slides.
- **One idea per slide.** Do not cram multiple topics into one slide.
- **Use variety:** Mix bullet lists, code blocks, short paragraphs, and bold/italic emphasis across slides. Not every slide should be a bullet list.
- **Code blocks:** Use `<pre><code>` for code examples. Keep them short (under 12 lines).
- **No images or external resources.** Everything must be inline.
- **Slide numbers:** Add `<div class="slide-number">N / TOTAL</div>` to every slide.

## Rules

- The output MUST be a single, self-contained `.html` file with no external dependencies.
- The file MUST be valid HTML5 that opens correctly by double-clicking.
- NEVER generate placeholder or lorem ipsum content — all slide content must be real and relevant to the topic.
- If the topic is too broad, narrow the scope and tell the user what you focused on.
- If you don't know enough about the topic to fill 8 slides with accurate content, tell the user and ask for guidance rather than making things up.
