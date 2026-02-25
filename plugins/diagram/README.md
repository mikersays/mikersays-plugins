# diagram

Generate a self-contained, interactive SVG diagram from a plain-text description. Zero dependencies — pure HTML, CSS, and minimal JS.

## Usage

```
/diagram microservice architecture with API gateway, auth service, and database
/diagram user login sequence diagram
/diagram CI/CD pipeline flowchart
/diagram users, orders, products ER diagram
```

## What it does

1. Reads your description and detects the diagram type from keywords
2. Plans 5–25 nodes and their connections based on your description
3. Generates a single `.html` file with an inline, interactive SVG diagram
4. Opens the file in your default browser

## Diagram types

The skill selects a diagram type based on keywords in your description. If no keywords match, it defaults to **Architecture**.

| Type | Trigger keywords |
|------|-----------------|
| Architecture | "architecture", "system", "service", "microservice", "component" |
| Sequence | "sequence", "flow of", "interaction", "request", "call" |
| Flowchart | "flowchart", "pipeline", "process", "workflow", "steps" |
| **Entity-Relationship** (**ER**) | "ER", "entity", "relationship", "schema", "table", "database model" |

If your description matches multiple types, the skill uses the first match in the table order above.

## Features

- **Pan and zoom** — drag to pan; use the `+`, `−`, and reset buttons or your mouse wheel to zoom
- **Hover tooltips** — hover over any node to see a description
- **Dark theme** — matches other mikersays plugins
- **Self-contained** — no CDN, no frameworks, just one HTML file

## Output

The skill saves a `<topic-slug>-diagram.html` file in your current directory, then opens it in your default browser. If the browser cannot open automatically, the skill prints the file path so you can open it manually.

The 25-node limit keeps diagrams readable. If your description implies more than 25 nodes, the skill groups related items and tells you what it combined.

## Installation

```bash
/plugin install diagram@mikersays-plugins
```
