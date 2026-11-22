---
name: lipsync-sheet
description: Make a 12-shape mouth sheet (viseme set) for a pixel-art portrait with the PixelLab MCP server, look at every frame and label what it really shows, and build a clean sheet in which only the mouth changes. Trigger on "viseme sheet", "mouth shapes for a character", "PixelLab vocal animation", "talking portrait sprites", "label the mouth frames", or "make a character that can talk".
argument-hint: "[character description or PixelLab character id] [mood]"
allowed-tools: Bash, Read, Write
---

# lipsync-sheet: a PixelLab viseme set, labeled by eye

This skill does one job: produce `<mood>.png`, a 1536x128 strip of 12 cells
(128x128 each) with one mouth shape per cell, in this fixed order:

`rest`, `closed`, `small_open`, `medium_open`, `wide_open`, `smile`,
`round_small`, `pucker`, `teeth`, `hiss`, `tongue`, `jaw_drop`

It needs the PixelLab MCP server (`mcp__pixellab__*` tools, a subscription)
and `uv`.

## Locate the script

```bash
LS="$CLAUDE_PLUGIN_ROOT/scripts"
[ -f "$LS/viseme_sheet.py" ] || LS="$(find ~/.claude/plugins ~/.codex/plugins -type d -path '*/lipsync/scripts' -print -quit 2>/dev/null)"
[ -f "$LS/viseme_sheet.py" ] && echo "scripts: $LS" || echo "lipsync scripts not found"
```

If this prints "lipsync scripts not found", the plugin is not installed
where expected; report that and stop.

## 1. Generate (about 21 generations per character and mood)

Call `get_balance` before and after: the difference is the only reliable
cost figure, because `get_vocal_animation` does not report what a job cost.
Keep at most 6 jobs active, or fewer if the user sets a lower limit.

1. **Character** (2 generations):
   `create_character(description="<age, role, hair, skin, headwear, clothes with colors>, clearly visible mouth", name="<Name>", size=64, mode="v3")`.
   Wait with `wait_for_jobs`, then `get_character` for the south rotation URL.
2. **Portrait** (15 generations at 128 px):
   `create_portrait_character(image_url="<south URL>", direction="character_to_portrait", result_size=128, seed=11)`,
   then `get_portrait_character`. Leave `view` at its default. Look at
   the portrait. Then attach it (free):
   `set_character_portrait(character_id, from_job_id="<portrait job>")`.
3. **Mouth positions** (about 4 generations per mood):
   `create_vocal_animation(character_id, mood="neutral", viseme_count=12, engine="pixminimax", seed=7)`.
   Poll `get_vocal_animation`. A job takes 4 to 15 minutes. Make `neutral`
   first; other moods (`happy`, `angry`, `sad`, `surprised`) can borrow its
   closed mouths.

Use 128 px: at 64 px the mouth is about 6 px wide and the 12 shapes merge.
Use `engine="pixminimax"`: `v3` costs 24 generations at this size and moves
the eyes and brows.

Do not use `create_talking_gif` or `get_lip_sync` for timing. They map
letters at a fixed frame length and never read the audio.

## 2. Download and look at every frame

```bash
uv run "$LS/viseme_sheet.py" fetch --character-id <uuid> --out raw
uv run "$LS/viseme_sheet.py" inspect raw/vocal-neutral-grid.png review/neutral-raw.png --box 24,40,104,112
```

Open `review/neutral-raw.png` (add `--zoom 8` for single pixels). For each
of the 12 frames, write down what the mouth shows. A frame has the lips
together only when no dark gap, tooth, or tongue pixel shows between the
lips; a nearly closed pucker is not closed. **Do not trust the frame
order.** PixelLab names the positions in the order above, but the drawings
do not always match. In 7 sheets made on 2026-11-22:

- One mood had no frame with the lips together: `rest` showed parted lips
  with teeth, and `closed` showed a broad smile with teeth.
- `rest` showed parted lips in another sheet (its `closed` was closed).
- `smile` showed closed lips in two sheets, and a thin slit in a third.
- `tongue` showed no tongue in two sheets.
- `jaw_drop` was the smallest opening in one sheet.
- `teeth` and `hiss` were weak in one sheet (a teeth line, a tiny gap).

The sheet draws transparent pixels in magenta, so the background around
the head (often a corner of the tile) is magenta too. Magenta inside a
mouth means the background removal cut white teeth out; the build fills
such holes.

## 3. Write `labels.json`

```json
{
 "labeled_by": "<who looked, and when>",
 "moods": {
  "neutral": {
   "frames": ["0: lips together, relaxed", "1: lips together", "... one line per raw frame ..."],
   "use": {"rest": 0, "closed": 1, "small_open": 2, "medium_open": 3, "wide_open": 4, "smile": 5,
           "round_small": 6, "pucker": 7, "teeth": 8, "hiss": 9, "tongue": 10, "jaw_drop": 11}
  },
  "happy": {
   "frames": ["0: lips parted, upper teeth show (PixelLab position: rest). Not closed.", "..."],
   "base": 8,
   "use": {"rest": "neutral:0", "closed": "neutral:1", "small_open": 8, "...": 0}
  }
 }
}
```

- `use` names, for each of the 12 shapes, the raw frame that shows it best:
  an index in this mood, or `"<mood>:<index>"` to borrow from another mood.
  One frame may serve two shapes; a useless frame goes unused.
- `rest` and `closed` **must** point at frames with the lips together. The
  frame plan shows them on silence and on p, b, m.
- `base` supplies everything outside the mouth. It defaults to the `rest`
  frame. Set it when `rest` is borrowed.
- Order the open shapes by the height of the opening, judged by eye:
  `small_open` < `medium_open` < `wide_open` <= `jaw_drop`. When no frame is
  taller than `wide_open`, use the same frame for `jaw_drop`.

## 4. Build

```bash
uv run "$LS/viseme_sheet.py" build --raw raw --labels labels.json \
    --mouth-box 44,70,84,98 --mood-box happy=40,66,88,100 --threshold 60 --out sheet
uv run "$LS/viseme_sheet.py" inspect sheet/neutral.png review/neutral-built.png --box 24,40,104,112
```

`--mouth-box x0,y0,x1,y1` is in cell pixels (x1 and y1 are outside the
box). It must contain the largest mouth of the mood with 2 px to spare, and
stay off the eyes and the nose tip. The numbers above are one character's;
find your own:

```bash
uv run "$LS/viseme_sheet.py" inspect raw/vocal-neutral-grid.png review/neutral-ruler.png \
    --box 24,40,104,112 --ruler --show-box 44,67,84,90
```

`--ruler` labels every 8th cell pixel along the top and left of each tile.
Read the left, top, right, and bottom of the largest mouth (lips included)
across all 12 frames, add 2 px on each side, and pass the result as
`--show-box`: the yellow outline must enclose every mouth. Boxes that
worked: 40x28 (a woman, neutral), 48x34 (her smile), 46x24 (a bearded man),
54x34 (a goblin's grin). A smile is wider, so a mood can have its own box
(`--mood-box`).

The build prints, for each shape, how many pixels of the cell differ from
the base. The number grows with the mouth and with how much beard or cheek
changes; equal numbers for two shapes are not an error. It also prints how
many pixels the `closed` cell differs from the `rest` cell; 0 means they
are the same picture, which is fine.

Why a build is needed: the raw frames differ from each other all over the
head (5,000 to 7,700 of 16,384 pixels in one character), and some move the
whole head by 1 or 2 px, so they shimmer in sequence. The build shifts each
frame onto the base, finds the changed pixels inside the mouth box, copies
only those onto the base, snaps them to the palette, and fills tooth holes.

Look at the built sheet:

- Every cell shows the mouth that its shape names.
- No mouth is cut by a straight edge (else enlarge the box).
- No teeth are black or speckled (else lower `--threshold` to 40).
- No seam shows in the cheeks or the beard.
- `rest` and `closed` show closed lips.

## Cost measured

2 + 15 + about 4 per mood. Three characters with two moods each were quoted
75 generations and cost 81 (gap-fill passes). A fourth with one mood cost
exactly 21.

## Gotchas

- The portrait step changes the character: one sprite had a bob and a
  mustard sweater, and its portrait had long hair and a black hoodie; a
  description with "short stubble that leaves the lips clear" got a full
  beard. The mouth shapes still worked, because they draw their own mouths.
- A portrait with an open grin is fine: the mouth set has its own closed
  frames, and the base is the `rest` frame, not the portrait.
- `viseme_count` must be the same for every mood of a character.
- A second mood turns the stored grid into two rows; `fetch` cuts the rows
  apart.
- `set_character_portrait` overwrites the portrait. Finish the portrait
  before you make mouth positions.

## Tested on, and not

Tested: four humanoid busts (two men with beards, a woman, a goblin) at
128 px, moods `neutral` and `happy`, `viseme_count=12`, PixMiniMax. Not
tested: animals, side views, 64 px or 256 px portraits, the moods `angry`,
`sad`, and `surprised`, 3, 5, or 7 positions, and portraits drawn outside
PixelLab.
