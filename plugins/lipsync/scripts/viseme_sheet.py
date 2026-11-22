#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "pillow",
#     "numpy",
# ]
# ///
"""Build 12-shape mouth sheets from a PixelLab character's raw mouth grids.

Three subcommands:

  fetch    Download a PixelLab character's ZIP (no token needed) into a raw
           folder: `rotations/*.png`, `portrait.png`, `metadata.json`, and one
           `vocal-<mood>-grid.png` per mood row of the mouth grid (a strip of
           square cells). A file that already exists is never overwritten: a
           changed file is saved as `<name>.new.<ext>` and reported, so that a
           reroll cannot silently replace reviewed art.
  inspect  Write a zoomed inspection sheet of a strip: every cell with its
           index, 4 per row, over magenta so that transparent holes stand out.
           Look at the result before you write `labels.json`: the cell order
           does not prove what a cell shows.
  build    Build the final viseme sheets from the raw grids.

PixelLab `create_vocal_animation` returns one 128x128 frame per mouth
position. The frames differ from the rest frame all over the head, not only
at the mouth: the engine redraws the beard, the hair, and the clothes with
small shifts, so the raw frames shimmer when they play in sequence. `build`
keeps only the mouth from each frame:

1. The base is the mood's `base` frame in `labels.json` (default: the frame
   used for `rest`). It supplies every pixel outside the mouth.
   Each other frame is first shifted by whole pixels (up to MAX_SHIFT each
   way) to the offset where it best matches the base outside the mouth box,
   because the engine sometimes moves the whole head by a few pixels.
2. Inside the mouth box, find the pixels whose color differs from the base by
   more than `--threshold`. Keep the connected groups of at least
   `--min-group` pixels, grow them by 1 px, and fill their holes. This is the
   frame's mouth mask.
3. The output frame is the base with the masked pixels taken from the raw
   frame, snapped to the palette (the base colors plus MOUTH_COLORS mouth
   colors). Transparent holes inside the mask are filled with the tooth color
   first: the engine's background removal sometimes cuts white teeth out.
4. The frames are written in the fixed SHAPES order, whatever order the raw
   grid has. `labels.json` holds, for each mood, `frames` (what each raw
   frame shows, in raw order), `use` (shape name -> raw frame index, or
   "<mood>:<index>" to borrow a mouth from another mood's grid) and optionally
   `base`. Write both after looking at every frame. One raw frame may serve two
   shapes, and a raw frame that shows the wrong mouth may go unused.
   `rest` and `closed` must point at frames with the lips together.

labels.json:
    {"moods": {"neutral": {"frames": ["0: lips together", ...],
                           "use": {"rest": 0, "closed": 1, ..., "smile": "happy:5"},
                           "base": 0}}}

`build` writes to --out: `<mood>.png` (12 cells in SHAPES order),
`<mood>@4x.png`, `<mood>-shapes.gif`, `palette.json` and `build-report.json`
(pixels changed from the base and the registration shift, per mood and shape).
It fails when a mood's `use` does not name all 12 shapes.

Usage:
    uv run viseme_sheet.py fetch --character-id <uuid> --out raw/
    uv run viseme_sheet.py inspect raw/vocal-neutral-grid.png look.png --box 44,70,84,98
    uv run viseme_sheet.py build --raw raw/ --labels labels.json \\
        --mouth-box 44,70,84,98 --mood-box happy=40,66,88,100 --threshold 60 --min-group 4 --out sheets/
    uv run viseme_sheet.py --selftest
Exit code 0 on success; non-zero with a one-line reason on failure.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

URL = "https://api.pixellab.ai/mcp/characters/{id}/download"

# The 12 mouth positions of `create_vocal_animation(viseme_count=12)`, in the
# order of the final sheets.
SHAPES = [
    "rest", "closed", "small_open", "medium_open", "wide_open", "smile",
    "round_small", "pucker", "teeth", "hiss", "tongue", "jaw_drop",
]
MOUTH_COLORS = 20  # colors added to the base palette for mouth interiors
MAX_SHIFT = 10     # largest head shift, in pixels, that registration searches
DEFAULT_THRESHOLD = 60
DEFAULT_MIN_GROUP = 6


def parse_box(text: str) -> list[int]:
    parts = [int(v) for v in text.split(",")]
    if len(parts) != 4 or parts[0] >= parts[2] or parts[1] >= parts[3]:
        raise ValueError(f"bad box {text!r}; use x0,y0,x1,y1 with x0 < x1 and y0 < y1")
    return parts


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------

def save(data: bytes, path: Path, root: Path) -> None:
    """Write `data` to `path`; a differing existing file stays and the new one gets `.new`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == data:
            return
        path = path.with_name(f"{path.stem}.new{path.suffix}")
        print(f"  differs from the stored raw; wrote {path.name}")
    path.write_bytes(data)
    print(f"  {path.relative_to(root)}")


def png_bytes(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def unpack_character(zdata: bytes, raw: Path) -> None:
    """Write the raw files of a character ZIP into `raw`."""
    from PIL import Image

    z = zipfile.ZipFile(io.BytesIO(zdata))
    meta = json.loads(z.read("metadata.json"))
    state = meta["states"][0]
    save(z.read("metadata.json"), raw / "metadata.json", raw)
    for direction, name in state["frames"]["rotations"].items():
        save(z.read(name), raw / "rotations" / f"{direction}.png", raw)
    if state.get("portrait"):
        save(z.read(state["portrait"]["path"]), raw / "portrait.png", raw)
    vocal = state.get("vocal_animation")
    if vocal:
        grid = Image.open(io.BytesIO(z.read(vocal["path"]))).convert("RGBA")
        row_h = grid.height // len(vocal["moods"])
        for i, mood in enumerate(vocal["moods"]):
            row = grid.crop((0, i * row_h, grid.width, (i + 1) * row_h))
            target = raw / f"vocal-{mood}-grid.png"
            if target.exists() and Image.open(target).convert("RGBA").tobytes() == row.tobytes():
                continue
            save(png_bytes(row), target, raw)
        print(f"  moods: {', '.join(vocal['moods'])}; positions: {', '.join(vocal['visemes'])}")


def cmd_fetch(a: argparse.Namespace) -> None:
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", a.character_id):
        raise ValueError("--character-id must be a PixelLab character UUID")
    with urllib.request.urlopen(URL.format(id=a.character_id), timeout=60) as r:
        zdata = r.read()
    unpack_character(zdata, a.out)


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------

def inspect_strip(strip: Path, out: Path, box: list[int], zoom: int, cell: int,
                  ruler: bool = False, show_box: list[int] | None = None) -> int:
    """Write the inspection sheet. Return the number of cells.

    `ruler` draws a tick every 8 cell pixels along the top and left of each
    tile, labeled with the cell coordinate, so a mouth's position can be
    read off the sheet. `show_box` outlines a proposed mouth box in yellow.
    """
    from PIL import Image, ImageDraw

    img = Image.open(strip).convert("RGBA")
    n = img.width // cell
    w, h = (box[2] - box[0]) * zoom, (box[3] - box[1]) * zoom
    cols = 4
    sheet = Image.new("RGB", (cols * (w + 8), -(-n // cols) * (h + 22)), (40, 40, 48))
    draw = ImageDraw.Draw(sheet)
    for i in range(n):
        c = img.crop((i * cell, 0, (i + 1) * cell, cell))
        flat = Image.new("RGBA", c.size, (255, 0, 255, 255))
        flat.alpha_composite(c)
        tile = flat.crop(tuple(box)).resize((w, h), Image.NEAREST).convert("RGB")
        x, y = (i % cols) * (w + 8), (i // cols) * (h + 22)
        sheet.paste(tile, (x, y + 18))
        draw.text((x + 4, y + 3), f"frame {i}", fill=(255, 255, 120))
        if ruler:
            for cx in range(-(-box[0] // 8) * 8, box[2], 8):
                px = x + (cx - box[0]) * zoom
                draw.line([(px, y + 18), (px, y + 24)], fill=(0, 255, 255))
                draw.text((px + 2, y + 24), str(cx), fill=(0, 255, 255))
            for cy in range(-(-box[1] // 8) * 8, box[3], 8):
                py = y + 18 + (cy - box[1]) * zoom
                draw.line([(x, py), (x + 6, py)], fill=(0, 255, 255))
                draw.text((x + 8, py - 5), str(cy), fill=(0, 255, 255))
        if show_box:
            bx0 = x + (show_box[0] - box[0]) * zoom
            by0 = y + 18 + (show_box[1] - box[1]) * zoom
            bx1 = x + (show_box[2] - box[0]) * zoom - 1
            by1 = y + 18 + (show_box[3] - box[1]) * zoom - 1
            draw.rectangle([bx0, by0, bx1, by1], outline=(255, 255, 0))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return n


def cmd_inspect(a: argparse.Namespace) -> None:
    box = parse_box(a.box) if a.box else [0, 0, a.cell, a.cell]
    n = inspect_strip(a.strip, a.out, box, a.zoom, a.cell, a.ruler,
                      parse_box(a.show_box) if a.show_box else None)
    print(f"{n} cells -> {a.out}")


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

def load_rgba(path: Path):
    import numpy as np
    from PIL import Image

    return np.array(Image.open(path).convert("RGBA")).astype(np.int32)


def cells(grid, cell: int) -> list:
    return [grid[:, i * cell:(i + 1) * cell] for i in range(grid.shape[1] // cell)]


def groups(mask) -> list[list[tuple[int, int]]]:
    """Return the 8-connected groups of True pixels."""
    import numpy as np

    seen = np.zeros_like(mask, bool)
    out = []
    h, w = mask.shape
    for y0, x0 in zip(*np.where(mask)):
        if seen[y0, x0]:
            continue
        stack, group = [(y0, x0)], []
        seen[y0, x0] = True
        while stack:
            y, x = stack.pop()
            group.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not seen[yy, xx]:
                        seen[yy, xx] = True
                        stack.append((yy, xx))
        out.append(group)
    return out


def grow(mask):
    """Grow a mask by 1 px in the four main directions."""
    out = mask.copy()
    out[1:, :] |= mask[:-1, :]
    out[:-1, :] |= mask[1:, :]
    out[:, 1:] |= mask[:, :-1]
    out[:, :-1] |= mask[:, 1:]
    return out


def fill_holes(mask):
    """Fill the False pixels that the mask fully encloses."""
    import numpy as np

    h, w = mask.shape
    outside = np.zeros_like(mask, bool)
    stack = [(y, x) for y in range(h) for x in (0, w - 1)] + \
            [(y, x) for x in range(w) for y in (0, h - 1)]
    while stack:
        y, x = stack.pop()
        if not (0 <= y < h and 0 <= x < w) or outside[y, x] or mask[y, x]:
            continue
        outside[y, x] = True
        stack += [(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)]
    return ~outside


def register(frame, base, cfg: dict):
    """Shift `frame` by whole pixels so that it lines up with `base`.

    The score is the mean color difference outside the mouth box, over the
    area where the shifted frame and the base overlap. Returns the shifted
    frame (transparent where it has no data) and the (dx, dy) applied.
    """
    import numpy as np

    cell = cfg["cell"]
    x0, y0, x1, y1 = cfg["mouth_box"]
    weight = np.ones((cell, cell), bool)
    weight[y0:y1, x0:x1] = False
    best, best_score = (0, 0), None
    for dy in range(-MAX_SHIFT, MAX_SHIFT + 1):
        for dx in range(-MAX_SHIFT, MAX_SHIFT + 1):
            ys = slice(max(0, dy), cell + min(0, dy))
            xs = slice(max(0, dx), cell + min(0, dx))
            yf = slice(max(0, -dy), cell + min(0, -dy))
            xf = slice(max(0, -dx), cell + min(0, -dx))
            w = weight[ys, xs]
            diff = np.abs(frame[yf, xf] - base[ys, xs]).sum(-1)
            score = diff[w].mean() + 0.01 * (abs(dx) + abs(dy))  # prefer no shift on a tie
            if best_score is None or score < best_score:
                best, best_score = (dx, dy), score
    dx, dy = best
    out = np.zeros_like(frame)
    ys = slice(max(0, dy), cell + min(0, dy))
    xs = slice(max(0, dx), cell + min(0, dx))
    yf = slice(max(0, -dy), cell + min(0, -dy))
    xf = slice(max(0, -dx), cell + min(0, -dx))
    out[ys, xs] = frame[yf, xf]
    return out, best


def mouth_mask(frame, base, cfg: dict):
    import numpy as np

    cell = cfg["cell"]
    x0, y0, x1, y1 = cfg["mouth_box"]
    delta = np.abs(frame[..., :3] - base[..., :3]).sum(-1)
    changed = (delta > cfg["threshold"]) | (frame[..., 3] != base[..., 3])
    box = np.zeros((cell, cell), bool)
    box[y0:y1, x0:x1] = True
    changed &= box
    keep = np.zeros_like(changed)
    for g in groups(changed):
        if len(g) >= cfg["min_group"]:
            for y, x in g:
                keep[y, x] = True
    if not keep.any():
        return keep
    keep = fill_holes(grow(keep)) & box
    return keep


def fill_tooth_holes(frame, mask):
    """Fill the transparent pixels inside the mouth mask with the tooth color.

    PixelLab's background removal (`no_background=True`) sometimes cuts white
    teeth out of a frame, which leaves transparent holes in the mouth. The
    fill color is the lightest opaque color inside the same mask.
    """
    import numpy as np

    holes = mask & (frame[..., 3] == 0)
    if not holes.any():
        return frame
    solid = frame[mask & (frame[..., 3] > 0)][:, :3]
    light = solid[solid.sum(-1).argmax()] if len(solid) else np.array([232, 232, 220])
    if light.sum() < 450:  # no tooth-colored pixel survived; use a neutral off-white
        light = np.array([232, 232, 220])
    out = frame.copy()
    out[holes, :3] = light
    out[holes, 3] = 255
    return out


def snap(rgb, palette):
    """Snap an (N, 3) color array to the nearest palette color."""
    d = ((rgb[:, None, :] - palette[None, :, :]) ** 2).sum(-1)
    return palette[d.argmin(1)]


def build_palette(base_frames: list, mouth_pixels):
    """Return the base frames' colors plus MOUTH_COLORS mouth colors."""
    import numpy as np
    from PIL import Image

    colors = {tuple(c[:3]) for f in base_frames for c in f.reshape(-1, 4) if c[3]}
    if len(mouth_pixels):
        strip = Image.fromarray(mouth_pixels.astype(np.uint8).reshape(1, -1, 3), "RGB")
        q = strip.quantize(MOUTH_COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        pal = np.array(q.getpalette()[:MOUTH_COLORS * 3]).reshape(-1, 3)
        used = sorted(set(np.array(q).reshape(-1).tolist()))
        colors |= {tuple(int(v) for v in pal[i]) for i in used}
    return np.array(sorted(colors), dtype=np.int32)


def build(raw_dir: Path, labels: dict, mouth_box: list[int], mood_boxes: dict[str, list[int]],
          threshold: int, min_group: int, out: Path, cell: int = 128) -> dict:
    """Build the sheets for every mood in `labels`. Return the report."""
    import numpy as np
    from PIL import Image

    moods = labels["moods"]
    for mood, lab in moods.items():
        if sorted(lab["use"]) != sorted(SHAPES):
            raise ValueError(f"{mood}: `use` must name each of the 12 shapes once")
    grids = {}
    for mood in moods:
        grids[mood] = cells(load_rgba(raw_dir / f"vocal-{mood}-grid.png"), cell)
    raw: dict[str, dict] = {}
    bases: dict[str, object] = {}
    cfgs: dict[str, dict] = {}
    for mood, lab in moods.items():
        use = lab["use"]
        if len(lab["frames"]) != len(grids[mood]):
            raise ValueError(f"{mood}: `frames` must describe all {len(grids[mood])} raw frames")

        def pick(ref):
            # A reference is a raw frame index in this mood, or "<mood>:<index>".
            if isinstance(ref, int):
                return grids[mood][ref]
            other, idx = ref.split(":")
            return grids[other][int(idx)]

        raw[mood] = {shape: pick(use[shape]) for shape in SHAPES}
        bases[mood] = pick(lab.get("base", use["rest"]))
        cfgs[mood] = {"cell": cell, "threshold": threshold, "min_group": min_group,
                      "mouth_box": mood_boxes.get(mood, mouth_box)}

    # Pass 1: masks and the pixels that define the mouth colors.
    masks: dict = {}
    shifts: dict[str, list[int]] = {}
    mouth_px = []
    for mood, frames in raw.items():
        base, mcfg = bases[mood], cfgs[mood]
        for shape in SHAPES:
            frames[shape], shift = register(frames[shape], base, mcfg)
            shifts[f"{mood}/{shape}"] = list(shift)
            m = mouth_mask(frames[shape], base, mcfg)
            masks[mood, shape] = m
            frames[shape] = fill_tooth_holes(frames[shape], m)
            mouth_px.append(frames[shape][m][:, :3])
    palette = build_palette(list(bases.values()), np.concatenate(mouth_px))

    # Pass 2: composite and write.
    out.mkdir(parents=True, exist_ok=True)
    report = {}
    closed_vs_rest: dict[str, int] = {}
    for mood, frames in raw.items():
        base = bases[mood]
        sheet = np.zeros((cell, cell * len(SHAPES), 4), np.int32)
        for k, shape in enumerate(SHAPES):
            m = masks[mood, shape]
            c = base.copy()
            if m.any():
                c[m, :3] = snap(frames[shape][m][:, :3], palette)
                c[m, 3] = 255
            sheet[:, k * cell:(k + 1) * cell] = c
            report[f"{mood}/{shape}"] = int((c != base).any(-1).sum())
            if shape == "closed":
                closed_vs_rest[mood] = int((c != sheet[:, :cell]).any(-1).sum())
        img = Image.fromarray(sheet.astype(np.uint8), "RGBA")
        img.save(out / f"{mood}.png")
        img.resize((img.width * 4, img.height * 4), Image.NEAREST).save(out / f"{mood}@4x.png")
        tiles = [img.crop((k * cell, 0, (k + 1) * cell, cell)).resize((cell * 4, cell * 4), Image.NEAREST)
                 for k in range(len(SHAPES))]
        flat = [Image.alpha_composite(Image.new("RGBA", t.size, (30, 30, 46, 255)), t).convert("P", palette=Image.Palette.ADAPTIVE)
                for t in tiles]
        flat[0].save(out / f"{mood}-shapes.gif", save_all=True, append_images=flat[1:], duration=350, loop=0)

    pal = {f"c{i:02d}": "#%02x%02x%02x" % tuple(int(v) for v in c) for i, c in enumerate(palette)}
    (out / "palette.json").write_text(json.dumps(pal, indent=1) + "\n")
    result = {"shapes": SHAPES, "palette_colors": len(palette),
              "registration_shift_xy": shifts,
              "pixels_changed_from_base": report,
              "closed_differs_from_rest_px": closed_vs_rest}
    (out / "build-report.json").write_text(json.dumps(result, indent=1) + "\n")
    return result


def cmd_build(a: argparse.Namespace) -> None:
    labels = json.loads(a.labels.read_text())
    mood_boxes = {}
    for item in a.mood_box or []:
        mood, _, box = item.partition("=")
        if not box:
            raise ValueError(f"bad --mood-box {item!r}; use mood=x0,y0,x1,y1")
        mood_boxes[mood] = parse_box(box)
    result = build(a.raw, labels, parse_box(a.mouth_box), mood_boxes, a.threshold, a.min_group, a.out, a.cell)
    print(f"{len(labels['moods'])} mood(s), palette {result['palette_colors']} colors -> {a.out}")
    for k, v in result["pixels_changed_from_base"].items():
        print(f"  {k:24s} {v:5d} px differ from base, shift {result['registration_shift_xy'][k]}")
    for mood, n in result["closed_differs_from_rest_px"].items():
        print(f"  {mood}: the closed cell differs from the rest cell in {n} px")


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest() -> None:
    # Pure-Python part: boxes and the `use` rule.
    assert parse_box("44,70,84,98") == [44, 70, 84, 98]
    for bad in ("1,2,3", "5,5,4,9"):
        try:
            parse_box(bad)
            raise AssertionError(f"accepted {bad!r}")
        except ValueError:
            pass
    assert len(SHAPES) == 12 and len(set(SHAPES)) == 12
    try:
        import numpy as np
        from PIL import Image
    except ImportError as e:
        print(f"SKIP: sheet build needs numpy and pillow (missing: {e.name})")
        return
    import random
    import zipfile as zf

    cell = 64
    box = [22, 38, 42, 50]
    rng = random.Random(1)

    def face(k: int, shift: int = 0, hole: bool = False) -> "np.ndarray":
        a = np.zeros((cell, cell, 4), np.uint8)
        yy, xx = np.mgrid[0:cell, 0:cell]
        a[(yy - 30) ** 2 + (xx - 32) ** 2 <= 26 ** 2] = (220, 170, 140, 255)
        a[24:27, 22:26] = (20, 20, 40, 255)   # eyes
        a[24:27, 38:42] = (20, 20, 40, 255)
        # Mouth rectangle: a different size and color for each frame.
        w, h = 6 + k, 2 + k % 5
        x0, y0 = 32 - w // 2, 40
        a[y0:y0 + h, x0:x0 + w] = (110 + 8 * k, 20, 40 + 5 * k, 255)
        if hole:
            a[y0:y0 + 2, x0 + 1:x0 + 4] = (0, 0, 0, 0)  # background removal cut the teeth out
        # Noise outside the mouth box: small color changes on the face.
        for _ in range(25):
            y, x = rng.randrange(8, 20), rng.randrange(20, 44)
            a[y, x, :3] = (a[y, x, :3].astype(int) + rng.randrange(-20, 20)).clip(0, 255)
        if shift:
            a = np.roll(a, shift, axis=1)
            a[:, :shift] = 0
        return a

    frames = [face(k, shift=2 if k == 3 else 0, hole=(k == 5)) for k in range(12)]
    grid = np.concatenate(frames, axis=1)
    labels = {"moods": {
        "neutral": {"frames": [f"{k}: test mouth" for k in range(12)],
                    "use": {s: k for k, s in enumerate(SHAPES)}},
        "happy": {"frames": [f"{k}: test mouth" for k in range(12)],
                  "use": {**{s: k for k, s in enumerate(SHAPES)}, "tongue": "neutral:7"}},
    }}
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        raw, out = tmp / "raw", tmp / "out"
        raw.mkdir()
        for mood in ("neutral", "happy"):
            Image.fromarray(grid, "RGBA").save(raw / f"vocal-{mood}-grid.png")
        res = build(raw, labels, box, {}, DEFAULT_THRESHOLD, 4, out, cell=cell)
        assert res["registration_shift_xy"]["neutral/medium_open"] == [-2, 0], res["registration_shift_xy"]
        assert res["registration_shift_xy"]["neutral/rest"] == [0, 0]
        sheet = np.array(Image.open(out / "neutral.png").convert("RGBA")).astype(int)
        assert sheet.shape == (cell, cell * 12, 4), sheet.shape
        base = sheet[:, :cell]
        outside = np.ones((cell, cell), bool)
        outside[box[1]:box[3], box[0]:box[2]] = False
        for k in range(12):
            c = sheet[:, k * cell:(k + 1) * cell]
            assert (c[outside] == base[outside]).all(), f"cell {k}: pixels outside the mouth box changed"
            if k:
                assert (c != base).any(), f"cell {k} shows no mouth"
        # Frame 5 (smile) had a transparent hole inside its mouth: the build fills it.
        smile = sheet[:, 5 * cell:6 * cell]
        w, h = 6 + 5, 2 + 0
        x0 = 32 - w // 2
        assert (smile[40:42, x0 + 1:x0 + 4, 3] == 255).all(), "tooth hole not filled"
        assert (out / "neutral@4x.png").exists() and (out / "happy-shapes.gif").exists()
        assert json.loads((out / "palette.json").read_text()) and (out / "build-report.json").exists()
        # `use` must name all 12 shapes.
        bad = {"moods": {"neutral": {"frames": labels["moods"]["neutral"]["frames"], "use": {"rest": 0}}}}
        try:
            build(raw, bad, box, {}, 60, 4, out, cell=cell)
            raise AssertionError("accepted a `use` with missing shapes")
        except ValueError:
            pass
        # inspect writes one tile per cell.
        n = inspect_strip(raw / "vocal-neutral-grid.png", tmp / "look.png", box, 3, cell)
        assert n == 12 and (tmp / "look.png").exists()
        # fetch: unpack a synthetic character ZIP, then again with a changed file.
        buf = io.BytesIO()
        with zf.ZipFile(buf, "w") as z:
            meta = {"states": [{"frames": {"rotations": {"south": "south.png"}},
                                "portrait": {"path": "portrait.png"},
                                "vocal_animation": {"path": "vocal.png", "moods": ["neutral", "happy"],
                                                    "visemes": SHAPES}}]}
            z.writestr("metadata.json", json.dumps(meta))
            for name in ("south.png", "portrait.png"):
                z.writestr(name, png_bytes(Image.new("RGBA", (8, 8), (1, 2, 3, 255))))
            two_rows = Image.new("RGBA", (cell * 2, cell * 2), (9, 9, 9, 255))
            z.writestr("vocal.png", png_bytes(two_rows))
        unpack_character(buf.getvalue(), tmp / "fetched")
        got = sorted(str(p.relative_to(tmp / "fetched")) for p in (tmp / "fetched").rglob("*") if p.is_file())
        assert got == ["metadata.json", "portrait.png", "rotations/south.png",
                       "vocal-happy-grid.png", "vocal-neutral-grid.png"], got
        (tmp / "fetched" / "portrait.png").write_bytes(b"changed")
        (tmp / "fetched" / "metadata.json").write_bytes(b"{}")
        unpack_character(buf.getvalue(), tmp / "fetched")
        assert (tmp / "fetched" / "portrait.new.png").exists() and (tmp / "fetched" / "metadata.new.json").exists()
        assert (tmp / "fetched" / "portrait.png").read_bytes() == b"changed"  # never overwritten
    print("selftest OK: viseme_sheet")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build 12-shape mouth sheets from PixelLab raw mouth grids.")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    sub = ap.add_subparsers(dest="cmd")

    f = sub.add_parser("fetch", help="download a PixelLab character's raw files")
    f.add_argument("--character-id", required=True, help="PixelLab character UUID")
    f.add_argument("--out", type=Path, required=True, help="raw folder to write")

    i = sub.add_parser("inspect", help="write a zoomed inspection sheet of a strip")
    i.add_argument("strip", type=Path)
    i.add_argument("out", type=Path)
    i.add_argument("--box", help="crop each cell to x0,y0,x1,y1 (default: the whole cell)")
    i.add_argument("--zoom", type=int, default=5)
    i.add_argument("--ruler", action="store_true", help="label every 8th cell pixel along the top and left of each tile")
    i.add_argument("--show-box", help="outline a proposed mouth box x0,y0,x1,y1 in yellow")
    i.add_argument("--cell", type=int, default=128, help="cell size in pixels (default 128)")

    b = sub.add_parser("build", help="build the final viseme sheets")
    b.add_argument("--raw", type=Path, required=True, help="folder with vocal-<mood>-grid.png files")
    b.add_argument("--labels", type=Path, required=True, help="labels.json")
    b.add_argument("--mouth-box", required=True, help="x0,y0,x1,y1 of the mouth area")
    b.add_argument("--mood-box", action="append", metavar="MOOD=BOX", help="mouth box for one mood (repeatable)")
    b.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD,
                   help=f"color difference that counts as changed (default {DEFAULT_THRESHOLD})")
    b.add_argument("--min-group", type=int, default=DEFAULT_MIN_GROUP,
                   help=f"smallest group of changed pixels to keep (default {DEFAULT_MIN_GROUP})")
    b.add_argument("--cell", type=int, default=128, help="cell size in pixels (default 128)")
    b.add_argument("--out", type=Path, required=True, help="folder to write")

    a = ap.parse_args(argv)
    if a.selftest:
        selftest()
        return 0
    if not a.cmd:
        ap.error("choose a subcommand: fetch, inspect or build")
    try:
        {"fetch": cmd_fetch, "inspect": cmd_inspect, "build": cmd_build}[a.cmd](a)
    except ImportError as e:
        print(f"error: missing package {e.name}; run this script with `uv run`", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, IndexError, zipfile.BadZipFile) as e:
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
