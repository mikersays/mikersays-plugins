---
name: diagram
description: Generate an interactive SVG diagram (architecture, sequence, flowchart, ER) from a description
argument-hint: "[description of what to diagram]"
allowed-tools: Write, Bash
---

# Diagram

Generate a single self-contained HTML file with an interactive (pan, zoom, hover-tooltip) SVG diagram. Supported types: architecture, sequence, flowchart, entity-relationship.

## Process

1. **Get the description.** If `$ARGUMENTS` is non-empty, use it. Otherwise ask the user what to diagram.

2. **Detect the type** from keywords in the description. If multiple match, take the first row in this table; if none match, default to architecture.

   | Type | Keywords |
   |------|----------|
   | Architecture | architecture, system, service, microservice, component |
   | Sequence | sequence, flow of, interaction, request, call |
   | Flowchart | flowchart, pipeline, process, workflow, steps |
   | ER | ER, entity, relationship, schema, table, database model |

3. **Plan 5–25 nodes.** For each node, decide on a 1–4 word label, a one-sentence tooltip, and its connections (with optional 1–3 word edge labels). If the description implies more than 25 nodes, group related items and tell the user what you grouped — past 25 the diagram stops being readable. If the description is too vague to plan meaningfully, ask for more detail rather than inventing nodes.

4. **Lay out the nodes.** See `references/layouts.md` for the spacing, shape, and colour conventions per diagram type. Read only the section for the type you detected.

5. **Compute the viewBox.** Take the bounding box of all nodes plus 60px padding on every side. Default size is `0 0 1200 800`; widen it (e.g. `0 0 1600 1000`) for diagrams that need more room. Update both the `<svg viewBox="...">` attribute and the `vb` / `INIT` constants in the script so pan/zoom reset correctly.

6. **Build the HTML** by copying `references/template.html` verbatim, then filling in the title, subtitle (`TYPE · N nodes`), viewBox, and the `<!-- DIAGRAM CONTENT -->` block with your `.node` and `.edge` elements. The template already contains the arrowhead `<marker id="arrow">`, the colour palette, the pan/zoom/tooltip script, and the dark theme — do not duplicate or rewrite those.

7. **Write and open the file.** Save as `<topic-slug>-diagram.html` (lowercase, hyphens) in the current working directory. Then `open <file>` on macOS, `xdg-open <file>` on Linux. If the open command fails, print the absolute path so the user can open it manually.

8. **Report** the file path, diagram type, and node count.

## Node and edge markup

Every node is a `<g class="node node-<colour>">` with `data-label` (display name) and `data-tooltip` (one-sentence description) attributes. The script reads those attributes to render the tooltip — without them the node still draws but loses its hover behaviour.

```svg
<g class="node node-violet" data-label="Auth Service" data-tooltip="Issues and validates JWT tokens.">
  <rect x="200" y="100" width="140" height="50" rx="8"/>
  <text x="270" y="125">Auth Service</text>
</g>

<g class="edge">
  <line x1="270" y1="150" x2="270" y2="220" marker-end="url(#arrow)"/>
  <text class="edge-label" x="285" y="190">JWT</text>
</g>
```

Available palette classes: `node-blue`, `node-indigo`, `node-violet`, `node-teal`, `node-green`, `node-cyan`, `node-slate`, `node-orange`, `node-amber`, `node-rose`. The CSS in the template styles `rect`, `circle`, and `polygon` children of each — pick the shape that matches the diagram type (rect for most things, polygon for decision diamonds, etc.).

## Layout invariants

These keep the output readable; ignore them only when the description forces a trade-off, and tell the user what you compromised.

- **Connect edges to node borders, not centres.** For a rect, intersect the line with the rectangle edge so the arrowhead doesn't disappear under the shape.
- **Leave at least 20px between any two nodes.** Touching shapes read as one blob.
- **Don't route edges through unrelated nodes.** If a straight line would cross a node, use a single-elbow path around it.
- **Edge labels stay short (1–3 words).** Drop the label entirely if the relationship is obvious from context.
- **Every node comes from the description.** Don't invent placeholder or filler nodes to balance the layout.

## Output constraints

- Single self-contained `.html` file. No external CSS, JS, fonts, or CDN links — the file should work fully offline. The template is built around this, so just don't add `<link>` or `<script src=...>` tags.

## Reference files

- `references/template.html` — the full HTML template to copy. Read once per invocation.
- `references/layouts.md` — per-type layout conventions. Read only the relevant section.
