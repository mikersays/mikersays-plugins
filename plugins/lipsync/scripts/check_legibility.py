#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "pillow",
# ]
# ///
"""Can the 1-bit mouth shapes of a small panel be told apart?

Needs Pillow. Input: one or more art strips for a 1-bit panel, each a
horizontal PNG with one full-panel cell per mouth shape (the `oled` strip of
`device_pack.py`). The defaults are the 128x64 OLED layout: 7 cells of
128x64 (closed, teeth, small, open, wide, smile, round) and the mouth box
40,40,48,24. `--panel-file`, `--shapes`, `--cell` and `--mouth-box` change
them.

Part 1, by count. Every pair of mouth shapes of a strip is compared inside
the mouth box (48x24 = 1152 pixels on the OLED). The distance of a pair is
the number of pixels that differ. Pass: every pair of every strip differs by
at least `--min-pixels` pixels (default 40). Exit code 0 on pass, 1 on fail;
the last line of part 1 is `LEGIBILITY PASS` or `LEGIBILITY FAIL`.

Part 2, by eye. `--trials DIR --key key.json` writes each cell as its own
PNG at 1x, in a shuffled order under neutral names (`trial-01.png` ...), and
writes which shape each one shows to the key. A reader who has never seen
the art names the shape in each file, from the list of shape names alone.
`--score answers.json --key key.json` then prints the confusion matrix
(`answers.json` maps a trial name to the shape named). The count cannot
tell whether a shape reads as the right mouth; the reader can. Keep the key
away from the reader.

Usage:
    uv run check_legibility.py --strip wren=oled/wren.png [--strip juno=oled/juno.png] [--out result.json]
    uv run check_legibility.py --strip wren=oled/wren.png --trials trials/ --key key.json
    uv run check_legibility.py --strip wren=oled/wren.png --key key.json --score answers.json
    uv run check_legibility.py --selftest

A strip is `name=path` or a bare path (the name is then the file's stem).
`--seed N` changes the shuffle (default 20261122).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
from pathlib import Path

MIN_PIXELS = 40  # of the 1152 mouth-box pixels of the 128x64 layout
DEFAULT_SHAPES = ["closed", "teeth", "small", "open", "wide", "smile", "round"]
DEFAULT_CELL = (128, 64)
DEFAULT_MOUTH_BOX = (40, 40, 48, 24)
DEFAULT_SEED = 20261122


def cells(strip_path: Path, shapes: list[str], cell: tuple[int, int]) -> dict:
    """Cut a strip into one 1-bit image per shape (a pixel is lit at 128 or more)."""
    from PIL import Image
    w, h = cell
    strip = Image.open(strip_path).convert("L")
    if strip.size[0] < w * len(shapes) or strip.size[1] < h:
        raise ValueError(f"{strip_path} is {strip.size[0]}x{strip.size[1]}; {len(shapes)} cells of {w}x{h} "
                         f"need {w * len(shapes)}x{h}")
    lit = strip.point(lambda v: 255 if v >= 128 else 0)
    return {s: lit.crop((k * w, 0, (k + 1) * w, h)) for k, s in enumerate(shapes)}


def matrix(images: dict, box: tuple[int, int, int, int]) -> list[list[int]]:
    """Pixels that differ inside the mouth box, for every pair of shapes."""
    x, y, w, h = box
    boxes = [im.crop((x, y, x + w, y + h)).tobytes() for im in images.values()]
    return [[sum(p != q for p, q in zip(a, b)) for b in boxes] for a in boxes]


# The mouths are dark on a lit face: the cell with the smallest mouth must
# still light this share of the mouth box.
MIN_LIT = 0.80


def outside_and_lit(images: dict, box: tuple[int, int, int, int]) -> tuple[int, float]:
    """(pixels outside the mouth box that differ between any two cells,
    lit share of the mouth box in the most lit cell)."""
    x, y, w, h = box
    ims = list(images.values())
    masked = []
    for im in ims:
        m = im.copy()
        m.paste(0, (x, y, x + w, y + h))
        masked.append(m.tobytes())
    stray = max(sum(p != q for p, q in zip(masked[0], other)) for other in masked)
    lit = max(sum(1 for v in im.crop((x, y, x + w, y + h)).tobytes() if v) for im in ims) / (w * h)
    return stray, lit


def count_check(strips: dict[str, Path], shapes: list[str], cell: tuple[int, int],
                box: tuple[int, int, int, int], min_pixels: int) -> dict:
    """Part 1 for every strip. Prints each matrix; returns the result."""
    result = {"shapes": shapes, "mouth_box": list(box), "min_pixels_required": min_pixels, "strips": {}}
    for name, path in strips.items():
        images = cells(path, shapes, cell)
        m = matrix(images, box)
        stray, lit = outside_and_lit(images, box)
        pairs = [(m[i][j], shapes[i], shapes[j]) for i in range(len(shapes)) for j in range(i + 1, len(shapes))]
        low = min(pairs)
        result["strips"][name] = {"matrix": m, "closest_pair": [low[1], low[2]], "closest_pixels": low[0],
                                  "pixels_changed_outside_box": stray, "most_lit_mouth_box": round(lit, 3)}
        print(f"\n{name}: pixels that differ in the mouth box")
        print(" " * 8 + "".join(f"{s:>7}" for s in shapes))
        for s, row in zip(shapes, m):
            print(f"{s:>8}" + "".join(f"{v:>7}" for v in row))
        print(f"closest pair: {low[1]} / {low[2]}, {low[0]} pixels")
        print(f"pixels that change outside the mouth box: {stray} (must be 0)")
        print(f"lit share of the mouth box in the most lit cell: {lit:.0%} (must be at least {MIN_LIT:.0%})")
    worst = min(c["closest_pixels"] for c in result["strips"].values())
    result["closest_pixels"] = worst
    result["pass"] = (worst >= min_pixels
                      and all(c["pixels_changed_outside_box"] == 0 for c in result["strips"].values())
                      and all(c["most_lit_mouth_box"] >= MIN_LIT for c in result["strips"].values()))
    return result


def write_trials(strips: dict[str, Path], shapes: list[str], cell: tuple[int, int], out_dir: Path,
                 seed: int = DEFAULT_SEED) -> dict:
    """Part 2, step 1: one 1x PNG per cell under a neutral name. Return the key."""
    out_dir.mkdir(parents=True, exist_ok=True)
    items = [(name, s) for name in strips for s in shapes]
    random.Random(seed).shuffle(items)
    cut = {name: cells(path, shapes, cell) for name, path in strips.items()}
    key = {}
    for n, (name, shape) in enumerate(items, 1):
        trial = f"trial-{n:02d}.png"
        cut[name][shape].convert("1").save(out_dir / trial)
        key[trial] = {"strip": name, "shape": shape}
    return key


def score(key: dict, answers: dict, shapes: list[str]) -> dict:
    """Part 2, step 2: the reader's confusion matrix. Prints it; returns the result."""
    conf = {s: {t: 0 for t in shapes + ["other"]} for s in shapes}
    right = 0
    for trial, truth in key.items():
        said = answers.get(trial, "other")
        said = said if said in shapes else "other"
        conf[truth["shape"]][said] += 1
        right += said == truth["shape"]
    print("\nreader's confusion matrix (rows: shown, columns: named)")
    print(" " * 8 + "".join(f"{s:>7}" for s in shapes + ["other"]))
    for s in shapes:
        print(f"{s:>8}" + "".join(f"{conf[s][t]:>7}" for t in shapes + ["other"]))
    print(f"LEGIBILITY READER: named {right} of {len(key)} frames correctly")
    return {"trials": len(key), "correct": right, "confusion": conf,
            "rows": "the shape shown", "columns": "the shape the reader named"}


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def selftest() -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError as e:
        print(f"SKIP: the legibility check needs pillow (missing: {e.name})")
        return
    import contextlib
    import io
    shapes = ["shut", "half", "full"]
    cell, box = (32, 16), (8, 8, 16, 8)
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        # Lit cells with a dark mouth of 2, 12 and 60 pixels inside the box.
        strip = Image.new("L", (96, 16), 255)
        d = ImageDraw.Draw(strip)
        d.rectangle([10, 10, 11, 10], fill=0)
        d.rectangle([32 + 10, 10, 32 + 15, 11], fill=0)
        d.rectangle([64 + 10, 9, 64 + 21, 13], fill=0)
        path = tmp / "a.png"
        strip.convert("1").save(path)
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink):
            res = count_check({"a": path}, shapes, cell, box, 10)
            assert res["strips"]["a"]["matrix"] == [[0, 10, 58], [10, 0, 48], [58, 48, 0]], res
            assert res["pass"] and res["closest_pixels"] == 10 and res["strips"]["a"]["closest_pair"] == ["shut", "half"]
            assert not count_check({"a": path}, shapes, cell, box, 11)["pass"]
            # Trials: every cell once, the same order for the same seed, and
            # the files hold the cells.
            key = write_trials({"a": path, "b": path}, shapes, cell, tmp / "trials")
            assert key == write_trials({"a": path, "b": path}, shapes, cell, tmp / "again")
            assert len(key) == 6 and sorted(v["shape"] for v in key.values()) == sorted(shapes * 2)
            first = key["trial-01.png"]
            shown = Image.open(tmp / "trials" / "trial-01.png")
            assert shown.size == cell
            assert shown.convert("L").tobytes() == cells(path, shapes, cell)[first["shape"]].tobytes()
            # A reader who calls every "half" a "full" and skips one file.
            answers = {t: ("full" if v["shape"] == "half" else v["shape"]) for t, v in key.items()}
            del answers[next(t for t, v in key.items() if v["shape"] == "shut")]
            r = score(key, answers, shapes)
            assert r["correct"] == 3 and r["confusion"]["half"]["full"] == 2 and r["confusion"]["shut"]["other"] == 1, r
        assert "closest pair: shut / half, 10 pixels" in sink.getvalue()
        try:
            cells(path, shapes + ["extra"], cell)
            raise AssertionError("a strip with too few cells must fail")
        except ValueError:
            pass
    print("selftest OK: check_legibility")


def _ints(text: str, n: int, what: str) -> tuple:
    parts = text.replace("x", ",").split(",")
    if len(parts) != n:
        raise ValueError(f"{what} takes {n} numbers, got {text!r}")
    return tuple(int(p) for p in parts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check that 1-bit mouth shapes can be told apart.")
    ap.add_argument("--strip", action="append", default=[], help="name=path of a 1-bit art strip; repeat for more")
    ap.add_argument("--panel-file", type=Path, help="panel description (JSON) with shapes, cell or panel, mouth_box")
    ap.add_argument("--shapes", help="cell names in strip order, comma-separated")
    ap.add_argument("--cell", help="size of one strip cell, WxH (default 128x64)")
    ap.add_argument("--mouth-box", help="X,Y,W,H inside a cell (default 40,40,48,24)")
    ap.add_argument("--min-pixels", type=int, default=MIN_PIXELS, help="fewest pixels two shapes may differ by (default 40)")
    ap.add_argument("--trials", type=Path, help="write one 1x PNG per cell here, shuffled; needs --key")
    ap.add_argument("--key", type=Path, help="the answer key: written with --trials, read with --score")
    ap.add_argument("--score", type=Path, help="answers.json from the reader; needs --key")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED, help="shuffle seed for --trials")
    ap.add_argument("--out", type=Path, help="write the result JSON here")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    a = ap.parse_args(argv)
    if a.selftest:
        selftest()
        return 0
    if not a.strip:
        ap.error("at least one --strip is required")
    if a.trials and not a.key:
        ap.error("--trials needs --key")
    if a.score and not a.key:
        ap.error("--score needs --key")
    try:
        import PIL  # noqa: F401
    except ImportError:
        print("error: Pillow is missing; run this script with `uv run`", file=sys.stderr)
        return 2
    try:
        spec = json.loads(a.panel_file.read_text()) if a.panel_file else {}
        shapes = [s.strip() for s in a.shapes.split(",")] if a.shapes else spec.get("shapes", DEFAULT_SHAPES)
        cell = _ints(a.cell, 2, "--cell") if a.cell else tuple(spec.get("cell") or spec.get("panel") or DEFAULT_CELL)
        box = _ints(a.mouth_box, 4, "--mouth-box") if a.mouth_box else tuple(spec.get("mouth_box", DEFAULT_MOUTH_BOX))
        strips: dict[str, Path] = {}
        for item in a.strip:
            name, _, path = item.rpartition("=")
            strips[name or Path(path).stem] = Path(path)
        result = count_check(strips, shapes, cell, box, a.min_pixels)
        print(f"\nLEGIBILITY {'PASS' if result['pass'] else 'FAIL'}: the closest pair differs by "
              f"{result['closest_pixels']} pixels; the minimum is {a.min_pixels}")
        if a.trials:
            key = write_trials(strips, shapes, cell, a.trials, a.seed)
            a.key.parent.mkdir(parents=True, exist_ok=True)
            a.key.write_text(json.dumps(key, indent=1) + "\n")
            print(f"{len(key)} trials in {a.trials}; key in {a.key}")
        if a.score:
            result["reader"] = score(json.loads(a.key.read_text()), json.loads(a.score.read_text()), shapes)
        if a.out:
            a.out.parent.mkdir(parents=True, exist_ok=True)
            a.out.write_text(json.dumps(result, indent=1) + "\n")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
