# Per-type layout recipes

Read the section for the diagram type you detected. Each section is self-contained.

## Architecture

- Layered top-to-bottom: clients -> API/gateway -> services -> data stores. Or left-to-right if the description reads that way.
- Node shape: rounded rect, 140x50, `rx="8"`.
- Spacing: layers 150px apart vertically, nodes 180px apart horizontally. Centre each layer in the viewBox.
- Colour by layer: blue=clients, indigo=gateways, violet=services, teal=databases, green=caches, cyan=queues.
- Group related services in a `<rect class="group-box">` with a `<text class="group-label">` above the top-left corner. The dashed group box reads as a logical boundary without competing with node strokes.
- Connect with straight lines or single-elbow paths.

## Sequence

- Participant boxes across the top: 140x40 rounded rects, evenly spaced.
- Vertical lifelines descending from each participant, dashed (`stroke-dasharray="6 4"`).
- Messages: horizontal arrows between lifelines, 60px apart vertically, label centred above the line.
- Solid arrows for synchronous calls; dashed (`stroke-dasharray="6 3"`) for async / responses — the visual distinction matches common UML convention.
- Self-call: U-shaped path looping to the right of the participant's lifeline.
- Colour participants by role using the palette.

## Flowchart

- Start/end: rounded rects, `rx="20"` (pill shape).
- Process steps: regular rects, `rx="8"`.
- Decisions: diamond polygons, e.g. `<polygon points="cx,cy-35 cx+70,cy cx,cy+35 cx-70,cy"/>`. Label inside.
- Flow top-to-bottom; decisions branch left/right with "Yes"/"No" edge labels.
- Spacing: 120px vertical between nodes; decision branches at least 200px apart horizontally so labels don't collide.
- Colour: blue=start/end, slate=processes, amber=decisions, green=success outcomes, rose=error outcomes.

## Entity-Relationship

- Each entity = a stack of rows. Header row 160x40 with the entity name in bold and a coloured palette fill. Attribute rows 160x24 below, alternating `style="fill:#0f1117"` / `style="fill:#151c29"` (inline `style`, not a `fill` attribute — the template's palette CSS overrides `fill` attributes on rects inside a `node-<colour>` group), left-aligned text.
- Mark primary keys with a key icon prefix in the attribute label.
- Relationship lines: straight or elbow paths, with cardinality labels (1, *, 1..*, etc.) at each end.
- Space entities at least 250px apart so attribute text stays readable when relationship lines pass nearby.
