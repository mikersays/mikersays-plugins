# roadmap

Generate a polished, interactive dark-theme HTML Gantt chart from a plain-text markdown roadmap file.

## Usage

```
/roadmap
/roadmap path/to/roadmap.md
```

## Input format

Write your roadmap as a simple markdown file grouped by month or phase. Tasks are quoted strings with date annotations:

```markdown
March 2026

- "Quality Review" until 3/20
- "Fix Gaps" until 3/27
- "Build Eval Framework" until 3/20
- "Public Beta" Begins 3/30

April 2026

- "Containerization Framework (Stable)" by 5/8
- "Deployment Pipeline" by 5/8

May 2026

- "Rollout" from 5/18-29
```

## What it generates

A single self-contained `roadmap.html` file with:

- **Gantt bars** — colour-coded by phase, proportionally placed across the timeline
- **Date ruler** — weekly tick marks with key milestone dates highlighted in bold
- **Milestone diamonds** — marked at every explicitly-stated end date, with pill labels floating above the bars
- **Hover tooltips** — cursor-tracking tooltip shows exact date range for each bar
- **Today line** — amber vertical line at the current date (or pinned to the left edge if today precedes the chart window)
- **Phase groupings** — tasks organised under labelled phase sections
- **Legend** — colour key at the bottom

The chart opens automatically in your default browser after generation.

## Features

- **Dark theme** — `#0f1117` background with light text
- **Responsive** — proportional layout scales with viewport width
- **Zero dependencies** — single HTML file, no CDN, no frameworks
- **Long labels wrap** — row labels never get clipped
- **Bars always on top** — grid lines render behind task bars (`z-index` layering)

## Installation

```bash
/plugin install roadmap@mikersays-plugins
```
