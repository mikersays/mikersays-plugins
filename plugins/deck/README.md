# deck

Generate a self-contained HTML slide deck from a topic. Zero dependencies — pure HTML, CSS, and minimal JS.

## Usage

```
/deck Intro to Kubernetes
/deck How Git works under the hood
/deck Why Rust is memory safe
```

## What it does

1. Takes your topic and plans 8–15 slides
2. Generates a single `.html` file with all styles and navigation inline
3. Opens the deck in your default browser

## Features

- **Keyboard navigation** — arrow keys and spacebar to advance
- **Scroll-snap slides** — each slide fills the viewport
- **Dark theme** — clean typography with a system font stack
- **Code blocks** — styled monospace with syntax-friendly colors
- **Responsive** — works on any screen size
- **Self-contained** — no CDN, no frameworks, just one HTML file

## Installation

```bash
/plugin install deck@mikersays-plugins
```
