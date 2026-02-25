# diagram

Generate interactive SVG diagrams from a plain-text description.

## Install

```bash
/plugin install diagram@mikersays-plugins
```

## Usage

```bash
/diagram microservice architecture with API gateway, auth service, and database
/diagram user login sequence diagram
/diagram CI/CD pipeline flowchart
/diagram users, orders, products ER diagram
```

## What it does

1. Detects the diagram type from your description (architecture, sequence, flowchart, or ER)
2. Generates a self-contained HTML file with an inline SVG diagram
3. Supports pan, zoom (buttons + mouse wheel), and hover tooltips
4. Opens the file in your default browser

## Diagram types

| Type | Detected when description contains |
|------|-------------------------------------|
| Architecture | "architecture", "system", "service", "microservice", "component" |
| Sequence | "sequence", "flow of", "interaction", "request", "call" |
| Flowchart | "flowchart", "pipeline", "process", "workflow", "steps" |
| ER | "ER", "entity", "relationship", "schema", "table", "database model" |

## Output

A single `.html` file in the current directory with:

- Dark theme matching other mikersays plugins
- Interactive SVG with pan and zoom
- Hover tooltips on every node
- Zoom controls (+, -, reset)
