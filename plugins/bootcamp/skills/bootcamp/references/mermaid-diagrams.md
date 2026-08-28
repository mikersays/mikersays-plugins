# Mermaid diagrams in HTML — render, expand, zoom

Any diagram you put in a page — a mermaid graph, a hand-written `<svg>`, an exported PNG —
must be **expandable and zoomable**. A flowchart that fits a text column is unreadable at
column width and worse on a phone, and a reader who cannot enlarge it cannot use it.

The contract for every diagram you ship:

- Clicking the diagram (or its **Expand** button) opens it full-screen.
- In the overlay the reader can zoom (scroll wheel, pinch, `+` / `−` buttons, `+`/`-`/`0` keys)
  and pan (drag, arrow keys), with a **Fit** control that returns to the whole diagram.
- `Esc`, the `✕` button, or a click on the backdrop closes it and returns focus to the page.
- Mermaid renders to SVG, so zooming stays sharp at any magnification — never ship a diagram
  as a low-resolution raster when the source can render as vector.

This skill bundles a dependency-free implementation. **Do not rewrite it per site** — copy it,
then theme it with the CSS variables listed below.

```
assets/diagram-zoom.js    ← ~350 lines, no dependencies, exposes window.DiagramZoom
assets/diagram-zoom.css   ← overlay + expand-button styling, themed via custom properties
```

Resolve them from `${CLAUDE_PLUGIN_ROOT}` (fall back to this file's directory if unset).

---

## 1. Render mermaid without a runtime CDN

Pages built by this plugin are no-build static files, so **vendor the mermaid bundle** instead of
loading it from a CDN at runtime — a CDN-dependent page breaks offline, on locked-down networks,
and whenever the CDN changes a "latest" build under you.

```bash
mkdir -p docs/assets/vendor
curl -fsSL -o docs/assets/vendor/mermaid.min.js \
  https://cdn.jsdelivr.net/npm/mermaid@11.17.2/dist/mermaid.min.js   # pin an exact version
```

The bundle is ~3.5 MB and gets committed. If that is unwelcome in the repo, pre-render instead
(§4) and ship only the resulting SVG.

Write each diagram as mermaid source inside `<pre class="mermaid">`:

```html
<figure class="diagram">
  <pre class="mermaid">
flowchart LR
  A[Client] --> B{Edge router}
  B -->|cache hit| C[CDN]
  B -->|miss| D[API gateway]
  </pre>
  <figcaption>Figure 1 — request path</figcaption>
</figure>
```

If mermaid fails to load, that block degrades to readable diagram source rather than an empty
box — which is why the source belongs in the page, not in a JS string.

## 2. Wire the zoom layer

Copy the two files into the site, then load them **after** mermaid and initialize in order.
`DIAGRAM_ZOOM_MANUAL` must be set *before* `diagram-zoom.js` runs, so that it waits for
mermaid's SVGs to exist instead of scanning an empty page:

```html
<link rel="stylesheet" href="assets/css/diagram-zoom.css">
...
<script>window.DIAGRAM_ZOOM_MANUAL = true;</script>
<script src="assets/vendor/mermaid.min.js"></script>
<script src="assets/js/diagram-zoom.js"></script>
<script>
  mermaid.initialize({ startOnLoad: false, theme: 'dark', securityLevel: 'strict' });
  mermaid.run({ querySelector: '.mermaid' })
    .then(function () { DiagramZoom.init(); })
    .catch(function (err) { console.error(err); DiagramZoom.init(); });
</script>
```

Set mermaid's `theme` to match the site (`'dark'`, `'default'`, `'neutral'`, or `themeVariables`
tuned to the design tokens) — the expanded view shows the same SVG, so a mismatch is visible.

**What `init()` picks up by default:** `.mermaid > svg`, `.diagram > svg`, `figure > svg`, and
anything marked `[data-zoomable]`. Add `data-zoomable` to any other diagram — including an
`<img>` of a diagram — or pass your own selector: `DiagramZoom.init({ selector: '.figure-svg' })`.
Calling `init()` again is safe: already-wired diagrams are skipped, so call it after inserting
diagrams dynamically.

A `<figcaption>` inside (or immediately after) the diagram's container becomes the overlay title
and the expand button's accessible name.

## 3. Theming

The overlay reads CSS custom properties and falls back to a dark palette. Set these on `:root`
in the site's own stylesheet — do not fork the file:

| Token | Purpose |
|---|---|
| `--dz-backdrop` | Full-screen overlay background (default `#080b12`) |
| `--dz-fg` | Overlay text and control foreground |
| `--dz-muted` | Zoom-level readout and the hint line |
| `--dz-border` | Control and divider borders |
| `--dz-chip-bg` / `--dz-chip-hover` | Button fill, resting and hover |
| `--dz-accent` | Focus ring |

On a light site, set at minimum `--dz-backdrop`, `--dz-fg`, and `--dz-muted`.

## 4. Single-file HTML (no `assets/` directory)

When the output is one self-contained file, do not link the assets — **inline** the contents of
`diagram-zoom.css` in a `<style>` block and `diagram-zoom.js` in a `<script>` block, unchanged.

Vendoring 3.5 MB of mermaid into a single file is not reasonable, so pre-render the diagram to
SVG at build time and embed that SVG:

```bash
npx -y @mermaid-js/mermaid-cli -i diagram.mmd -o diagram.svg -b transparent
```

If `mermaid-cli` is unavailable, hand-author the SVG rather than shipping a mermaid source block
that will never render. Either way, wrap it in `<figure class="diagram">` and the zoom layer
picks it up with no further work.

## 5. Verify before you ship

Load the page (`cd docs && python3 -m http.server 4173`) and confirm:

- [ ] Every diagram renders — no raw mermaid source left visible, no empty `<pre>`.
- [ ] Each diagram shows an **Expand** affordance and opens full-screen on click.
- [ ] In the overlay: wheel/pinch zoom, drag pan, `+` / `−` / **Fit**, and a sharp (not blurry)
      diagram at high zoom.
- [ ] `Esc` closes it and focus returns to the diagram that was opened.
- [ ] At a 390px-wide viewport the diagram still opens at a readable scale and pans.
- [ ] The browser console is clean.
