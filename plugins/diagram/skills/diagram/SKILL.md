---
name: diagram
description: Generate an interactive SVG diagram from a description
argument-hint: "[description of what to diagram]"
allowed-tools: Write, Bash
---

# Diagram — Generate an Interactive SVG Diagram

Generate a self-contained HTML file with an interactive SVG diagram. Supports architecture, sequence, flowchart, and ER diagrams.

## Process

1. **Get the description.** If the user provided text via `$ARGUMENTS`, use that. If `$ARGUMENTS` is empty, ask the user what they want to diagram.

2. **Detect the diagram type** from keywords in the description:

   | Type | Keywords |
   |------|----------|
   | **Architecture** | "architecture", "system", "service", "microservice", "component" |
   | **Sequence** | "sequence", "flow of", "interaction", "request", "call" |
   | **Flowchart** | "flowchart", "pipeline", "process", "workflow", "steps" |
   | **ER** | "ER", "entity", "relationship", "schema", "table", "database model" |

   If no keywords match, default to **architecture**. If multiple match, prefer the first match in the table order above.

3. **Plan the nodes and connections.** Identify 5–25 nodes and their relationships from the description. Each node needs:
   - A short label (1–4 words)
   - A tooltip description (1 sentence explaining what it does)
   - Connections to other nodes (with optional edge labels)

4. **Compute the layout.** Arrange nodes based on diagram type:
   - **Architecture**: layered top-to-bottom or left-to-right grouping (e.g., clients → API → services → data)
   - **Sequence**: participants across the top, messages as horizontal arrows top-to-bottom
   - **Flowchart**: top-to-bottom flow with decision diamonds branching left/right
   - **ER**: entities as rectangles with relationship lines, spread to minimize crossings

5. **Write the HTML file** using the Write tool. Save as `<topic-slug>-diagram.html` in the current working directory (lowercase, hyphens, no spaces).

6. **Open the file** in the user's default browser:
   - macOS: `open <file>`
   - Linux: `xdg-open <file>`
   - If the open command fails, tell the user the file path so they can open it manually.

7. **Report** the file path, diagram type, and node count to the user.

## HTML Template

The generated HTML file MUST follow this structure. Do not use external stylesheets, scripts, or CDN links.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DIAGRAM TITLE</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
    overflow: hidden;
    height: 100vh;
  }

  .container {
    background: #0f1117;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .header {
    padding: 1.5rem 2rem 1rem;
    border-bottom: 1px solid #1e293b;
  }

  .header h1 {
    font-size: 1.5rem;
    font-weight: 700;
    background: linear-gradient(135deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  .header .subtitle {
    font-size: 0.85rem;
    color: #64748b;
    margin-top: 0.25rem;
  }

  .controls {
    position: absolute;
    top: 1rem;
    right: 1.5rem;
    display: flex;
    gap: 0.5rem;
    z-index: 20;
  }

  .controls button {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    border: 1px solid #334155;
    background: #1e293b;
    color: #e2e8f0;
    font-size: 1.1rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.15s;
  }

  .controls button:hover {
    background: #334155;
  }

  .canvas {
    flex: 1;
    overflow: hidden;
    cursor: grab;
    position: relative;
  }

  .canvas:active {
    cursor: grabbing;
  }

  svg {
    width: 100%;
    height: 100%;
  }

  /* Node styles */
  .node rect, .node circle, .node polygon {
    stroke-width: 2;
    transition: filter 0.15s;
  }

  .node:hover rect, .node:hover circle, .node:hover polygon {
    filter: brightness(1.3);
  }

  .node text {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
    fill: #e2e8f0;
    text-anchor: middle;
    dominant-baseline: central;
    pointer-events: none;
  }

  /* Edge styles */
  .edge line, .edge path {
    stroke: #475569;
    stroke-width: 1.5;
    fill: none;
  }

  .edge polygon {
    fill: #475569;
    stroke: none;
  }

  .edge-label {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 11px;
    fill: #94a3b8;
    text-anchor: middle;
  }

  /* Tooltip */
  .tooltip {
    position: fixed;
    display: none;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 12px;
    box-shadow: 0 8px 24px rgba(0,0,0,.5);
    z-index: 1000;
    pointer-events: none;
    max-width: 280px;
  }

  .tooltip .tip-title {
    font-weight: 600;
    font-size: 0.85rem;
    color: #f1f5f9;
    margin-bottom: 2px;
  }

  .tooltip .tip-desc {
    font-size: 0.8rem;
    color: #94a3b8;
    line-height: 1.4;
  }

  /* Node colour palette */
  .node-blue rect    { fill: #1e3a5f; stroke: #3b82f6; }
  .node-indigo rect  { fill: #2e1065; stroke: #6366f1; }
  .node-violet rect  { fill: #3b0764; stroke: #8b5cf6; }
  .node-teal rect    { fill: #042f2e; stroke: #14b8a6; }
  .node-green rect   { fill: #052e16; stroke: #22c55e; }
  .node-cyan rect    { fill: #083344; stroke: #06b6d4; }
  .node-slate rect   { fill: #1e293b; stroke: #64748b; }
  .node-orange rect  { fill: #431407; stroke: #f97316; }
  .node-amber rect   { fill: #451a03; stroke: #f59e0b; }
  .node-rose rect    { fill: #4c0519; stroke: #f43f5e; }

  /* Same for circles (sequence participants) */
  .node-blue circle    { fill: #1e3a5f; stroke: #3b82f6; }
  .node-indigo circle  { fill: #2e1065; stroke: #6366f1; }
  .node-violet circle  { fill: #3b0764; stroke: #8b5cf6; }
  .node-teal circle    { fill: #042f2e; stroke: #14b8a6; }
  .node-green circle   { fill: #052e16; stroke: #22c55e; }
  .node-cyan circle    { fill: #083344; stroke: #06b6d4; }

  /* Diamonds (flowchart decisions) */
  .node-amber polygon  { fill: #451a03; stroke: #f59e0b; }
  .node-rose polygon   { fill: #4c0519; stroke: #f43f5e; }
</style>
</head>
<body>

<div class="container">
  <div class="header">
    <h1>DIAGRAM TITLE</h1>
    <p class="subtitle">TYPE · N nodes</p>
  </div>
  <div class="controls">
    <button onclick="zoomIn()" title="Zoom in">+</button>
    <button onclick="zoomOut()" title="Zoom out">−</button>
    <button onclick="resetView()" title="Reset view">⟲</button>
  </div>
  <div class="canvas" id="canvas">
    <svg id="svg" viewBox="0 0 1200 800">
      <!-- DIAGRAM CONTENT: groups of .node and .edge elements -->
    </svg>
  </div>
</div>

<div class="tooltip" id="tooltip">
  <div class="tip-title" id="tip-title"></div>
  <div class="tip-desc" id="tip-desc"></div>
</div>

<script>
const svg = document.getElementById('svg');
const canvas = document.getElementById('canvas');
const tooltip = document.getElementById('tooltip');
const tipTitle = document.getElementById('tip-title');
const tipDesc = document.getElementById('tip-desc');

// --- Viewbox state ---
let vb = { x: 0, y: 0, w: 1200, h: 800 };
const INIT = { ...vb };
let isPanning = false, startX, startY;

function applyVB() {
  svg.setAttribute('viewBox', `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
}

function zoomIn()  { zoom(0.8); }
function zoomOut() { zoom(1.25); }
function resetView() { vb = { ...INIT }; applyVB(); }

function zoom(factor) {
  const cx = vb.x + vb.w / 2, cy = vb.y + vb.h / 2;
  vb.w *= factor; vb.h *= factor;
  vb.x = cx - vb.w / 2; vb.y = cy - vb.h / 2;
  applyVB();
}

// Mouse wheel zoom
canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  zoom(e.deltaY > 0 ? 1.1 : 0.9);
}, { passive: false });

// Pan
canvas.addEventListener('mousedown', (e) => {
  isPanning = true; startX = e.clientX; startY = e.clientY;
});
window.addEventListener('mousemove', (e) => {
  if (!isPanning) return;
  const dx = (e.clientX - startX) * (vb.w / canvas.clientWidth);
  const dy = (e.clientY - startY) * (vb.h / canvas.clientHeight);
  vb.x -= dx; vb.y -= dy;
  startX = e.clientX; startY = e.clientY;
  applyVB();
});
window.addEventListener('mouseup', () => { isPanning = false; });

// Tooltips
document.querySelectorAll('.node[data-tooltip]').forEach(node => {
  node.addEventListener('mouseenter', (e) => {
    tipTitle.textContent = node.getAttribute('data-label') || '';
    tipDesc.textContent = node.getAttribute('data-tooltip') || '';
    tooltip.style.display = 'block';
  });
  node.addEventListener('mousemove', (e) => {
    let x = e.clientX + 12, y = e.clientY + 12;
    if (x + 280 > window.innerWidth) x = e.clientX - 292;
    if (y + 80 > window.innerHeight) y = e.clientY - 80;
    tooltip.style.left = x + 'px';
    tooltip.style.top = y + 'px';
  });
  node.addEventListener('mouseleave', () => {
    tooltip.style.display = 'none';
  });
});
</script>
</body>
</html>
```

## Layout Guidelines

### Architecture Diagrams
- Arrange nodes in horizontal layers: **Clients** (top) → **API/Gateway** → **Services** → **Data stores** (bottom)
- Use rounded rectangles (`rx="8"`) for all nodes, sized 140×50
- Connect nodes with straight lines or single-elbow paths
- Space layers 150px apart vertically, nodes 180px apart horizontally
- Colour by layer: blue for clients, indigo for gateways, violet for services, teal for databases, green for caches, cyan for queues

### Sequence Diagrams
- Draw participant boxes across the top (140×40 rounded rects)
- Vertical lifeline dashed lines descending from each participant
- Horizontal arrows between lifelines for each message, spaced 50px apart vertically
- Arrow labels centred above the line
- Use solid arrows for synchronous calls, dashed for async/responses
- Colour participants by role using the palette

### Flowchart Diagrams
- Start/end nodes: rounded rectangles with `rx="20"`
- Process steps: regular rectangles with `rx="8"`
- Decision points: diamond polygons (rotated squares), label inside
- Connect with straight or single-bend paths, arrowheads at end
- Flow top-to-bottom; branch decisions left/right
- Colour: blue for start/end, slate for processes, amber for decisions, green for success outcomes, rose for error outcomes

### ER Diagrams
- Entity rectangles: 160×40 header + attribute list below
- Header: entity name, bold, coloured fill from palette
- Attributes: 160×24 rows, alternating `#0f1117` / `#151c29` fill, left-aligned text
- Mark primary keys with a key icon (★) prefix
- Relationship lines: straight or elbow paths, with cardinality labels (1, *, 1..*, etc.) at each end
- Space entities at least 250px apart

## SVG Coordinate Rules

- Default viewBox: `0 0 1200 800` — adjust width/height if the diagram needs more space
- All positions use absolute SVG coordinates (not CSS)
- Arrowhead marker definition:
  ```svg
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5"
      markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569"/>
    </marker>
  </defs>
  ```
- Use `marker-end="url(#arrow)"` on edge lines/paths

## Rules

- The output MUST be a single, self-contained `.html` file with no external dependencies.
- Maximum 25 nodes. If the description implies more, group related items and tell the user.
- NEVER generate placeholder or dummy nodes — every node must come from the user's description.
- Every node MUST have a `data-tooltip` attribute with a meaningful description and a `data-label` attribute with the display name.
- Edge labels should be short (1–3 words). Omit labels if the relationship is obvious.
- Node labels should be 1–4 words. Truncate or abbreviate if needed.
- Nodes must not overlap. Leave at least 20px gap between any two nodes.
- The SVG viewBox must be large enough to contain all nodes with at least 40px padding on all sides.
- If the description is too vague to produce a meaningful diagram, ask the user for more detail rather than guessing.
