---
name: roadmap
description: Generate a self-contained interactive HTML Gantt chart from a markdown roadmap file
argument-hint: "[path/to/roadmap.md]"
allowed-tools: Read, Write, Bash, Glob
---

# Roadmap — Markdown to Interactive Gantt Chart

Turn a plain-text roadmap into a polished, dark-theme HTML Gantt chart with milestones, a today-line, and hover tooltips. Output is a single self-contained file (no CDN, no framework).

## 1. Locate the source

- If `$ARGUMENTS` has a path, use it.
- Else Glob the cwd for `roadmap.md`.
- If still missing, ask the user.

## 2. Parse the roadmap

Roadmaps look like this:

```markdown
March 2026
- "Quality Review" until 3/20
- "Fix Gaps" until 3/27
- "Public Beta" Begins 3/30

April 2026
- "Deployment Pipeline" by 5/8

May 2026
- "Rollout" from 5/18-29
```

Extract per task:

| Field | Source |
|---|---|
| **name** | the quoted string |
| **start** | explicit `from` / `Begins`; else the day after the previous task's end if that task is in the same section; else the first day of the section month |
| **end** | `until`, `by`, or the upper bound of `from X–Y`. A `Begins`-only task has no explicit end: extend its bar to the chart end and mark the end as inferred |
| **phase** | the section heading; assign sequential phase numbers |

Compute **chart start** = first day of the earliest month, **chart end** = last day of the latest. When a date is inferred rather than stated, remember it for the report in step 7 — users want to verify guesses.

If the file yields zero parseable tasks, do not generate HTML — show the user the expected format (the example above) and ask them to fix the file or point to another one.

## 3. Assign colours

Pick from this palette by task role; cycle if more than 10 tasks. Roles are guidance, not a contract — the goal is that adjacent phases read as visually distinct.

| Class | Hex | Typical role |
|---|---|---|
| `bar-blue`   | `#1d4ed8` | First task in Phase 1 |
| `bar-indigo` | `#4338ca` | Phase 1 build tasks |
| `bar-violet` | `#6d28d9` | Additional Phase 1 |
| `bar-teal`   | `#0f766e` | Fix / gap / patch |
| `bar-green`  | `#15803d` | Beta / launch |
| `bar-cyan`   | `#0e7490` | Infrastructure |
| `bar-slate`  | `#334155` | Pipeline / ops |
| `bar-orange` | `#c2410c` | Rollout / release |
| `bar-amber`  | `#b45309` | Warning / hotfix |
| `bar-rose`   | `#be123c` | Critical / urgent |

## 4. Identify milestones

Any task with an **explicit** end date is a milestone (inferred ends are not). Render:

- A 14×14 diamond marker at the end date (`transform: rotate(45deg)`).
- A pill label floating above the row. Use the amber highlight pill for phase boundaries and launches; plain dark pill otherwise — this keeps the eye drawn to the events that actually move the project forward.

## 5. Generate `roadmap.html`

Write next to the source file. Single file, inline CSS and JS.

### Page

- Background `#0f1117`, text `#e2e8f0`, system font stack, `min-width: 1100px`.
- `<h1>` title plus a subtitle showing the date range.

### Layout — fixed 280px label gutter

Every header, ruler, and grid element gets `margin-left: 280px`. Row labels sit in the gutter:

```css
position: absolute; left: -280px; width: 268px;
text-align: right; padding-right: 14px;
white-space: normal; line-height: 1.35; /* wrap, never clip */
```

Phase section headers above each group: `9px` uppercase.

### Month header & date ruler

- Month header: flex row of cells sized proportionally to each month's day count, labelled `Month YYYY`, left border aligned with the grid.
- Date ruler: `28px` tall, `margin-bottom: 8px`, ticks every 7 days.
  - Milestone dates (every task endpoint): `10px` tick, label `font-weight: 700; color: #94a3b8`.
  - Other dates: `6px` tick, label `color: #475569`.
  - Centre labels with `transform: translateX(-50%)`.

### Grid and bars — z-index matters

Grid lines must render *behind* bars; otherwise hairlines cut through the bars and the chart looks broken.

- Grid: `position: relative; margin-left: 280px; border-left: 1px solid #1e293b`. Month-boundary lines and weekly sub-grid lines (`background: #151c29`) at `z-index: 0`.
- Bars: `z-index: 2`, height `24px`, `top: 7px` in a `38px` row, `border-radius: 5px`. Truncate text with ellipsis. Hover: `filter: brightness(1.25)`.
- Position: `left = pct(daysFromStart)`, `width = pct(durationDays)` (see coordinate helper below).

### Milestone pills

```css
/* default */
background: rgba(15,17,23,0.88);
border: 1px solid #334155; border-radius: 999px;
padding: 2px 7px; font-size: 9px; font-weight: 700; color: #f1f5f9;
/* highlight (phase boundary / launch) */
background: rgba(251,191,36,0.15);
border-color: #fbbf24; color: #fde68a;
```

Pill position: `top: -2px; transform: translate(-50%, -100%)`. Diamond at `z-index: 6`.

### Today line

Compute with `new Date()` in JS:

- Inside the chart window: amber vertical line at the right offset, `z-index: 10`.
- Before chart start: pin to the left edge, label `"← TODAY (Mon DD)"` so the user still sees where "now" is.
- After chart end: hide.

### Hover tooltip

A `position: fixed` div, hidden by default, `z-index: 1000`. On bar `mouseenter` show name (with a coloured dot) and date range; on `mousemove` follow the cursor and clamp to viewport edges. Skip native `title=` attributes — they conflict with the custom tooltip.

Style: `background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 8px 12px; box-shadow: 0 8px 24px rgba(0,0,0,.5)`.

### Legend

Flex row at the bottom (`flex-wrap: wrap; gap: 20px`): one swatch per colour class actually used, plus a diamond for milestones and a dashed amber swatch for the today line.

### Coordinate helper

```js
const SPAN = (END - START) / 86400000; // days in chart
const pct = (day) => (day / SPAN) * 100;
```

Use `pct()` for every `left` and `width` so the chart scales with viewport width.

## 6. Open the file

Try to open in the default browser; fall back to printing the path. Always pass the absolute path of the file you just wrote — the output sits next to the source markdown, which may not be the cwd.

```bash
# macOS
open /abs/path/to/roadmap.html
# Linux
xdg-open /abs/path/to/roadmap.html
```

Detect platform via `uname` or `process.platform`. If the open command fails, just tell the user the absolute path.

## 7. Report back

- Output file path.
- Task count and phase count.
- Any dates that were inferred (so the user can verify).
