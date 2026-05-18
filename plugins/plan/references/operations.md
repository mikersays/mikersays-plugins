# Plan plugin — shared operations

Building blocks the `/plan-*` skills use. Each skill points back here for the operation it needs rather than duplicating the logic. Bash snippets target both macOS (BSD) and Linux (GNU); switch on `uname` when they diverge.

## Locate the plan directory

`docs/plan/` is resolved relative to the repo root:

```bash
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
[ -z "$ROOT" ] && { echo "Not inside a git repo."; exit 1; }
PLAN_DIR="$ROOT/docs/plan"
```

If the user isn't in a git repo, ask whether they want to run `git init` first — most planning history is worthless without version control.

## Find the next ID

Scan existing item filenames, take the highest numeric prefix, add one:

```bash
last=$(ls "$PLAN_DIR"/[0-9]*.md 2>/dev/null \
  | sed 's|.*/||; s|-.*||' \
  | sort -n | tail -1)
next_id=$(printf "%03d" $((10#${last:-0} + 1)))
```

The `10#` prefix forces base-10. Without it, bash reads any leading-zero string as octal — so `042` becomes `34` (giving the wrong next id) and `008` blows up entirely with "value too great for base." Apply the same trick anywhere you increment a zero-padded id.

When the directory is empty (no matching files), `last` is empty, `${last:-0}` becomes `0`, and `next_id` becomes `001`. The 3-digit pad keeps directories sortable up to 999; at 1000 the formula naturally produces `1000` (4 digits) and the next ID is `1001`. No code change needed.

**Collision defense:** Right before writing, check the slot is still empty. Two sessions racing might have both computed the same `next_id`:

```bash
attempt=0
while compgen -G "$PLAN_DIR/${next_id}-*.md" > /dev/null; do
  attempt=$((attempt + 1))
  [ "$attempt" -ge 5 ] && { echo "Too many ID collisions, aborting."; exit 1; }
  next_id=$(printf "%03d" $((10#$next_id + 1)))
done
```

The `10#$next_id` forces base-10 (bash treats leading-zero strings as octal otherwise — `08` will explode).

## Slugify a title

Lowercase, replace non-alphanumeric with `-`, collapse runs of `-`, trim, cap at 40 chars at a word boundary:

```bash
slug=$(printf '%s' "$title" \
  | tr '[:upper:]' '[:lower:]' \
  | sed 's|[^a-z0-9]|-|g; s|--*|-|g; s|^-||; s|-$||' \
  | cut -c1-40 \
  | sed 's|-$||')
[ -z "$slug" ] && slug="item-${next_id}"
```

The final fallback handles all-punctuation titles (`???` → empty slug). Without it the filename becomes `042-.md` and breaks the glob conventions.

## Parse the frontmatter

The frontmatter is the YAML block between the first two `---` lines. Extract it once:

```bash
fm=$(awk '/^---$/{c++; next} c==1' "$file")
```

Then pull a single field. Split on the FIRST `:` only — a naive `-F': *'` truncates titles like `Foo: bar` to `Foo`:

```bash
get_field() {
  awk -v key="$1" '
    index($0, key ":") == 1 {
      sub(/^[^:]*:[[:space:]]*/, "")
      print
      exit
    }
  ' <<< "$fm"
}

status=$(get_field status)
title=$(get_field title)
```

For the `tags: [a, b]` list, strip brackets and split on `,` — but for filtering purposes a substring match (`grep -q "$tag"`) on the raw line is almost always sufficient.

## Resolve a target (id-or-slug)

`/plan-update`, `/plan-close` accept either `7` (numeric) or `fix-login` (slug fragment).

```bash
resolve_target() {
  local q="$1"
  local matches=()
  if [[ "$q" =~ ^[0-9]+$ ]]; then
    # Numeric: zero-pad and glob. nullglob prevents an unmatched
    # pattern from being returned as a literal "match".
    local padded
    padded=$(printf "%03d" "$((10#$q))")
    shopt -s nullglob
    matches=( "$PLAN_DIR/${padded}-"*.md )
    shopt -u nullglob
  else
    # Slug: grep titles, case-insensitive. Use a read loop instead
    # of `mapfile` — macOS ships bash 3.2 which lacks mapfile.
    while IFS= read -r line; do
      [ -n "$line" ] && matches+=("$line")
    done < <(grep -li "^title:.*${q}" "$PLAN_DIR"/[0-9]*.md 2>/dev/null)
  fi
  case "${#matches[@]}" in
    0) echo "no-match"; return 1 ;;
    1) echo "${matches[0]}"; return 0 ;;
    *) printf '%s\n' "${matches[@]}"; return 2 ;;
  esac
}
```

Two portability fixes folded in:

- `shopt -s nullglob` around the numeric glob: a no-match pattern stays empty rather than returning the literal `$PLAN_DIR/007-*.md` as a single match (which then "succeeds" with a path to a file that doesn't exist).
- Read loop instead of `mapfile -t`: macOS ships with bash 3.2 which doesn't have `mapfile`. Claude's `Bash` tool inherits the system shell, so `mapfile` would fail on every macOS user.

When `return 2` (ambiguous), list candidates with `id | title` and ask the user to pick. When `return 1`, list the 3 closest IDs (numerically) if numeric, or "no match" if slug.

## Normalize a date

Accept ISO `2026-05-25`, words like `today`, `tomorrow`, `friday`, `next-friday`, or offsets like `+3d`, `+1w`. Output ISO.

```bash
normalize_date() {
  local input="$1"
  case "$input" in
    today)    date "+%Y-%m-%d" ;;
    tomorrow) [ "$(uname)" = "Darwin" ] && date -v+1d "+%Y-%m-%d" || date -d "tomorrow" "+%Y-%m-%d" ;;
    +*d)      n=${input#+}; n=${n%d}; [ "$(uname)" = "Darwin" ] && date -v+"${n}"d "+%Y-%m-%d" || date -d "+$n days" "+%Y-%m-%d" ;;
    +*w)      n=${input#+}; n=${n%w}; [ "$(uname)" = "Darwin" ] && date -v+"${n}"w "+%Y-%m-%d" || date -d "+$n weeks" "+%Y-%m-%d" ;;
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9])
              printf '%s' "$input" ;;
    *)        # weekday names — GNU date handles these natively, macOS doesn't.
              [ "$(uname)" = "Darwin" ] \
                && { echo "Can't parse '$input' on macOS — use ISO YYYY-MM-DD."; return 1; } \
                || date -d "$input" "+%Y-%m-%d" 2>/dev/null || { echo "Can't parse '$input'."; return 1; }
              ;;
  esac
}
```

When parsing fails, ask the user for an ISO date rather than guessing.

## Compute "today"

```bash
today=$(date "+%Y-%m-%d")
```

Use this everywhere instead of inlining `date "+%Y-%m-%d"` — single source of truth makes the skill testable.

## Regenerate `docs/plan/README.md`

Always do a full rewrite — never patch. The index is the rendered view of state; if conflicts happen, re-running any `/plan-*` command resolves them.

Layout:

````markdown
# Plan

<N> open · <M> in progress · <K> blocked · <J> done

## Open (N)

| ID | Title | Type | Pri | Due | Tags |
|----|-------|------|-----|-----|------|
| [012](012-add-search.md) | Add search to docs | feature | high | 2026-06-01 | docs |
| [008](008-fix-redirect.md) | Fix login redirect | bug | high | | auth |

## In progress (M)

...

## Blocked (K)

...

<details>
<summary>Done (J)</summary>

| ID | Title | Closed |
|----|-------|--------|
| [007](007-add-cache.md) | Add HTTP cache | 2026-05-15 |

</details>

---
*Auto-generated by `/plan-*` commands. Edit items directly in `docs/plan/`.*
````

Rules:

- Omit empty groups entirely (no `## Blocked` heading with zero rows).
- Within a group, sort by priority (high → med → low), then due ascending (items with `due` before items without), then ID descending.
- Empty cells render blank, not `-` or `null`.
- Title links use the filename (relative path), not the ID — GitHub renders them clickably from inside `docs/plan/`.

## Append a dated note to an item body

When the user adds context without changing structured fields, append after existing body:

```markdown

## <today>

<note text>
```

A blank line separates the note from prior content. If the file ends without a trailing newline, add one first.

## Bumping `updated:`

Every write (add, update, close) sets `updated:` to today. Easiest via `Edit`:

- Match the line `updated: <old-date>` and replace with `updated: <today>`.

For new items, write `updated: <today>` directly in the frontmatter template.
