---
name: roadmap
description: Generate a visual HTML Gantt-chart roadmap from a markdown roadmap file
argument-hint: "[path/to/roadmap.md]"
allowed-tools: Read, Write, Bash, Glob
---

# Roadmap — Generate a Visual HTML Gantt Chart

Read a plain-text roadmap markdown file and produce a polished, interactive dark-theme HTML Gantt chart.

## 1. Locate the source file

- If `$ARGUMENTS` contains a file path, use that.
- Otherwise search the current working directory for `roadmap.md` using Glob.
- If no file is found, ask the user where the roadmap file is.

Read the file with the Read tool.

## 2. Parse the roadmap

Extract every task. For each task identify:

| Field | How to find it |
|---|---|
| **name** | The quoted string, e.g. `"Quality Review"` |
| **start date** | An explicit `from` / `Begins` date, or infer from the section heading (e.g. `March 2026` → first day of that month) |
| **end date** | `until`, `by`, or the last date of a `from X–Y` range |
| **phase** | Group by section heading; assign sequential phase numbers |

Infer missing start dates from context (tasks under a month heading with no explicit start begin on the first of that month, or the day after the preceding task ends).

Determine the **chart start** (first day of the earliest month) and **chart end** (last day of the latest month).

## 3. Assign colours

Use this palette, cycling if there are more than 10 tasks:

| Class | Hex | Use for |
|---|---|---|
| `bar-blue`   | `#1d4ed8` | First task in Phase 1 |
| `bar-indigo` | `#4338ca` | Other Phase 1 build tasks |
| `bar-violet` | `#6d28d9` | Additional Phase 1 tasks |
| `bar-teal`   | `#0f766e` | Fix / gap / patch tasks |
| `bar-green`  | `#15803d` | Beta / launch tasks |
| `bar-cyan`   | `#0e7490` | Infrastructure tasks |
| `bar-slate`  | `#334155` | Pipeline / ops tasks |
| `bar-orange` | `#c2410c` | Rollout / release tasks |
| `bar-amber`  | `#b45309` | Warning / hotfix tasks |
| `bar-rose`   | `#be123c` | Critical / urgent tasks |

## 4. Identify milestones

Any task whose end date is explicitly stated (not just inferred) is a **milestone**. Mark it with:
- A diamond marker at the end date
- An amber-highlighted pill label for phase boundaries or launch events; plain dark pill otherwise

## 5. Generate the HTML file

Write the output to `roadmap.html` in the same directory as the source file.

### 5.1 Page structure & theme

- `background: #0f1117`, light text (`#e2e8f0`)
- Font: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- `min-width: 1100px`
- `<h1>` title + subtitle with date range

### 5.2 Left label column — width 280px

- `margin-left: 280px` on every header / ruler / grid element
- Row labels: `position: absolute; left: -280px; width: 268px; text-align: right; padding-right: 14px`
- Allow wrapping: `white-space: normal; line-height: 1.35` — never clip long names
- Phase section headers: `9px` uppercase labels above each group

### 5.3 Month header

Flex row of proportionally-sized cells labelled "Month YYYY". Left border on each cell aligns with the grid.

### 5.4 Date ruler

- Height `28px`, `margin-bottom: 8px`, same left offset as the grid
- Tick marks at every **7 days** across the full span
- **Key milestone dates** (every task endpoint in the roadmap): taller tick (`10px`), bold label (`font-weight: 700; color: #94a3b8`)
- Regular dates: short tick (`6px`), muted label (`color: #475569`)
- Labels centred with `transform: translateX(-50%)`

### 5.5 Grid

- `position: relative; margin-left: 280px; border-left: 1px solid #1e293b`
- Month-boundary lines: `z-index: 0`
- Weekly sub-grid lines: `background: #151c29; z-index: 0`
- **Both must render behind bars** — never overlay task bars

### 5.6 Task bars

- `z-index: 2` (always above grid lines)
- Height `24px`, `top: 7px` within a `38px` row, `border-radius: 5px`
- Text truncated: `overflow: hidden; text-overflow: ellipsis; white-space: nowrap`
- Hover: `filter: brightness(1.25)`
- Position and width computed as `(dayOffset / totalDays) * 100%`

### 5.7 Milestone markers

- Rotated 14×14px square (`transform: rotate(45deg)`), `z-index: 6`
- Pill label floated **above** the row: `top: -2px; transform: translate(-50%, -100%)`
- Default pill: `background: rgba(15,17,23,0.88); border: 1px solid #334155; border-radius: 999px; padding: 2px 7px; font-size: 9px; font-weight: 700; color: #f1f5f9`
- Highlight pill (phase boundaries / launches): `background: rgba(251,191,36,0.15); border-color: #fbbf24; color: #fde68a`

### 5.8 Today line

- Compute today with `new Date()` in JavaScript
- Within chart window: amber vertical line at the correct position, `z-index: 10`
- Before chart start: pin to left edge, label `"← TODAY (Mon DD)"`
- After chart end: hidden

### 5.9 Custom hover tooltip

- `position: fixed` div, hidden by default, `z-index: 1000`
- `mouseenter` each bar → show task name (coloured dot) + date range
- `mousemove` → follow cursor; clamp to viewport edges
- Style: `background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 8px 12px; box-shadow: 0 8px 24px rgba(0,0,0,.5)`
- No native `title=` attributes on bars

### 5.10 Legend

Flex row at bottom (`flex-wrap: wrap; gap: 20px`) — one colour swatch per unique class used, a diamond for milestones, a dashed amber swatch for the today line.

### 5.11 JavaScript coordinate system

```js
const SPAN = (END - START) / 86400000; // total days
function pct(day) { return (day / SPAN) * 100; }
```

Use `pct()` for all `left` and `width` values so the chart scales with the viewport.

## 6. Open the file

```bash
# macOS
open roadmap.html

# Linux
xdg-open roadmap.html
```

Detect the platform via `process.platform` or by checking `uname`. If the open command fails, tell the user the file path so they can open it manually.

## 7. Report back

Tell the user:
- The output file path
- How many tasks and phases were detected
- Any dates that were ambiguous or inferred (so they can verify)
