#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "pillow",
# ]
# ///
"""Export a device pack (`.pnpk`): one spoken line for a small screen, in one file.

A microcontroller cannot run the speech model. The computer synthesizes the
line and plans the frames; the device plays a pack. A pack holds the audio, a
base image for the whole panel, the mouth frames in the panel's own pixel
format, and the frame plan as runs (frame index, duration in audio samples).
`pn_player.h` (in the `lipsync-device` skill's `assets/device/lib/pnplayer/`)
gives the byte layout.

Needs `ffmpeg` on PATH (it resamples the WAV) and Pillow.

Inputs:
  --plan    a plan file from `viseme_plan.py`. A pixel-narrator
            `.timeline.json` has the same fields and works too. The exporter
            reads `fps`, `frames`, `silences`, `text` and `background`.
  --wav     the audio of the line.
  --strip   the art: a horizontal PNG strip with one cell per mouth shape.
  --target  a preset panel description: `oled` or `sticks3`.
            `--panel-file panel.json` gives your own, and single options
            (`--mouth-box`, `--shapes`, ...) override either.

Presets (`--print-preset NAME` prints one as JSON to edit):
  oled     128x64, 1 bit per pixel (SSD1306 or SH1106), pixel format
           `mono_vpage`. The strip has 7 cells of 128x64, each a whole
           panel: closed, teeth, small, open, wide, smile, round. The 12
           plan shapes map to the 7. Mouth box 40,40,48,24.
  sticks3  M5Stack StickS3: 135x240 ST7789, portrait, pixel format
           `rgb565_be`. The strip is the 12-cell 128 px sheet of
           `lipsync-sheet`, shown at 1x at (3, 44) over the plan's background
           color, so every art pixel is one panel pixel. `--caption` writes
           a name under the face. The mouth box is found from the art.

A panel description is a JSON object with these keys:
  panel         [width, height] in pixels
  pixel_format  "mono_vpage" (1 bit, 8-row pages, top pixel in bit 0) or
                "rgb565_be" (16 bits, high byte first, row by row)
  panel_fps     how often the simulator records the panel (60)
  cell          [width, height] of one strip cell
  cell_xy       [x, y] of the cell on the panel
  shapes        the cell names, in strip order (the device shapes)
  shape_map     plan shape -> device shape (`full_to_oled` is read as an
                alias); every shape in the plan's frames needs an entry
  closed_shapes the device shapes with the lips together
  base_shape    the device shape of the base image; pauses show it too
  mouth_box     [x, y, width, height] on the panel, or "auto": the smallest
                box that holds every pixel that differs between two shapes.
                For `mono_vpage` every value is a multiple of 8.
  background    "#rrggbb" behind the cell (default: the plan's `background`)
  caption, caption_y   optional text under the face (`rgb565_be` only)

Output: `--out line.pnpk`, and next to it `line.pnpk.json`: the frame names,
the closed frames, the runs as [start sample, frame index], and the sizes.
The simulator wrapper and the checks read the JSON; the device does not.

The frame list has one shape per 1/fps second, so a pause can begin up to
one plan frame before the mouth closes. A panel refreshes faster than the
plan and would show that. So each silent stretch of the audio (the plan's
`silences`) is cut into the runs at sample accuracy: the mouth shows the
base shape for the whole stretch.

Usage:
    uv run device_pack.py --plan plan.json --wav narration.wav --strip oled.png \\
        --target oled --out line.oled.pnpk
    uv run device_pack.py --plan plan.json --wav narration.wav --strip neutral.png \\
        --target sticks3 --caption WREN --out line.sticks3.pnpk
    uv run device_pack.py --print-preset oled
    uv run device_pack.py --selftest

Options: `--rate 16000` (audio sample rate in Hz), `--audio adpcm|pcm16|none`.
Exit code 0 on success; non-zero with a one-line reason on failure.

The caption uses Pillow's default font, so its pixels can change with the
Pillow version. This file is a single-file copy of `narrator/pack.py` of
pixel-narrator; that project's `checks/check_plugin_parity.py` fails when
the two write different packs.
"""

from __future__ import annotations

import argparse
import array
import json
import math
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

PIX_MONO_VPAGE, PIX_RGB565_BE = 1, 2
PIXEL_FORMATS = {"mono_vpage": PIX_MONO_VPAGE, "rgb565_be": PIX_RGB565_BE}
AUDIO_NONE, AUDIO_PCM16, AUDIO_IMA_ADPCM = 0, 1, 2
HEADER_SIZE = 64
HEADER_FORMAT = "<4sBBBB2H4H4HIIIHHIIIII"
MAX_FRAMES = 16
DEFAULT_RATE = 16000
ADPCM_BLOCK = 256  # bytes; 505 samples

# The 12 mouth shapes of a `lipsync-sheet` sheet, in cell order.
SHAPES = [
    "rest", "closed", "small_open", "medium_open", "wide_open", "smile",
    "round_small", "pucker", "teeth", "hiss", "tongue", "jaw_drop",
]

PRESETS: dict[str, dict] = {
    "oled": {
        "about": "128x64 1-bit OLED (SSD1306 or SH1106)",
        "panel": [128, 64], "pixel_format": "mono_vpage", "panel_fps": 60,
        "cell": [128, 64], "cell_xy": [0, 0],
        # The 7 mouth shapes that stay distinct at this size, in cell order.
        "shapes": ["closed", "teeth", "small", "open", "wide", "smile", "round"],
        "closed_shapes": ["closed"],
        "shape_map": {
            "rest": "closed",         # lips together
            "closed": "closed",       # lips pressed: one closed mouth serves both
            "small_open": "small",    # t, d, n, l
            "tongue": "small",        # th: the tongue tip is under 2 pixels here
            "medium_open": "open",    # k, g, e
            "wide_open": "wide",      # open vowels
            "jaw_drop": "wide",       # the tallest opening does not fit a second size
            "smile": "smile",         # ee: wide and flat
            "round_small": "round",   # o, r
            "pucker": "round",        # oo, w: one rounded mouth serves both
            "teeth": "teeth",         # f, v
            "hiss": "teeth",          # s, z, sh, ch: teeth together
        },
        # Every value is a multiple of 8, so the box is a whole number of
        # display tiles (8x8 pixels), the unit that the controller updates.
        "mouth_box": [40, 40, 48, 24],
        "base_shape": "closed",
    },
    "sticks3": {
        "about": "M5Stack StickS3, 135x240 ST7789, RGB565, portrait",
        "panel": [135, 240], "pixel_format": "rgb565_be", "panel_fps": 60,
        "cell": [128, 128], "cell_xy": [3, 44],
        "shapes": SHAPES,
        "closed_shapes": ["rest", "closed"],
        "shape_map": {s: s for s in SHAPES},
        "mouth_box": "auto",
        "base_shape": "rest",
        "caption_y": 190,
    },
}

CAPTION_INK = (231, 231, 231)
CAPTION_RULE = (252, 140, 0)  # the short line under the caption


class PackError(Exception):
    """A problem with the inputs; the message is the one-line reason."""


# ---------------------------------------------------------------------------
# Audio: IMA ADPCM in blocks that decode on their own
# ---------------------------------------------------------------------------

_IMA_STEP = [
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107,
    118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963,
    1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894,
    6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794,
    32767]
_IMA_INDEX = [-1, -1, -1, -1, 2, 4, 6, 8]


def _ima_step(code: int, predictor: int, index: int) -> tuple[int, int]:
    """Apply one 4-bit code. Return the new (predictor, index)."""
    step = _IMA_STEP[index]
    diff = step >> 3
    if code & 4:
        diff += step
    if code & 2:
        diff += step >> 1
    if code & 1:
        diff += step >> 2
    predictor = max(-32768, min(32767, predictor - diff if code & 8 else predictor + diff))
    index = max(0, min(88, index + _IMA_INDEX[code & 7]))
    return predictor, index


def adpcm_encode(pcm, block: int = ADPCM_BLOCK) -> bytes:
    """Encode int16 mono samples as IMA ADPCM in self-contained blocks.

    A block is a 4-byte header (first sample as int16, step index, 0), then
    4-bit codes, low nibble first. A block of B bytes holds 1 + (B - 4) * 2
    samples.
    """
    per_block = 1 + (block - 4) * 2
    samples = [int(v) for v in pcm]
    out = bytearray()
    index = 0
    for start in range(0, len(samples), per_block):
        chunk = samples[start:start + per_block]
        predictor = chunk[0]
        body = bytearray(block - 4)
        out += struct.pack("<hBB", predictor, index, 0)
        for n, target in enumerate(chunk[1:]):
            step = _IMA_STEP[index]
            delta = target - predictor
            code = 8 if delta < 0 else 0
            delta = abs(delta)
            if delta >= step:
                code |= 4
                delta -= step
            if delta >= step >> 1:
                code |= 2
                delta -= step >> 1
            if delta >= step >> 2:
                code |= 1
            predictor, index = _ima_step(code, predictor, index)
            body[n // 2] |= code << ((n & 1) * 4)
        out += body
    return bytes(out)


def adpcm_decode(data: bytes, n_samples: int, block: int = ADPCM_BLOCK) -> list[int]:
    """Decode what `adpcm_encode` wrote, with the same steps as `pn_player.c`."""
    per_block = 1 + (block - 4) * 2
    out = [0] * n_samples
    predictor = index = 0
    for pos in range(n_samples):
        base = (pos // per_block) * block
        k = pos % per_block
        if k == 0:
            predictor, index = struct.unpack_from("<hB", data, base)
            index = min(index, 88)
        else:
            code = (data[base + 4 + (k - 1) // 2] >> (((k - 1) & 1) * 4)) & 15
            predictor, index = _ima_step(code, predictor, index)
        out[pos] = predictor
    return out


def load_audio(wav: Path, rate: int) -> array.array:
    """Read an audio file as int16 mono at `rate` (ffmpeg resamples it)."""
    if not shutil.which("ffmpeg"):
        raise PackError("ffmpeg must be on PATH")
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(wav), "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"],
        capture_output=True)
    if proc.returncode != 0:
        raise PackError(f"ffmpeg could not read {wav}: {proc.stderr.decode(errors='replace').strip()[-200:]}")
    pcm = array.array("h")
    pcm.frombytes(proc.stdout[:len(proc.stdout) // 2 * 2])
    if sys.byteorder == "big":
        pcm.byteswap()
    return pcm


# ---------------------------------------------------------------------------
# Pixels: an image to the panel's own bytes
# ---------------------------------------------------------------------------

def mono_vpage(img) -> bytes:
    """1-bit image -> page bytes: one byte per column per 8 rows, top pixel in bit 0."""
    gray = img.convert("L")
    w, h = gray.size
    if h % 8 or w % 8:
        raise PackError(f"a 1-bit image must be a multiple of 8 on each side, got {w}x{h}")
    px = gray.tobytes()
    out = bytearray(w * h // 8)
    for page in range(h // 8):
        for x in range(w):
            v = 0
            for bit in range(8):
                if px[(page * 8 + bit) * w + x] >= 128:
                    v |= 1 << bit
            out[page * w + x] = v
    return bytes(out)


def rgb565_be(img) -> bytes:
    """RGB image -> 16 bits per pixel, high byte first, row by row."""
    px = img.convert("RGB").tobytes()
    out = bytearray(len(px) // 3 * 2)
    for i in range(len(px) // 3):
        r, g, b = px[i * 3], px[i * 3 + 1], px[i * 3 + 2]
        v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
        out[i * 2] = v >> 8
        out[i * 2 + 1] = v & 255
    return bytes(out)


def rgb565_to_rgb(img):
    """Return what an RGB565 panel shows for an RGB image (the simulator's rule)."""
    from PIL import Image
    five = [((v >> 3) << 3) | (v >> 5) for v in range(256)]
    six = [((v >> 2) << 2) | (v >> 6) for v in range(256)]
    r, g, b = img.convert("RGB").split()
    return Image.merge("RGB", (r.point(five), g.point(six), b.point(five)))


ENCODERS = {PIX_MONO_VPAGE: mono_vpage, PIX_RGB565_BE: rgb565_be}


# ---------------------------------------------------------------------------
# Art: the strip laid out on the panel, one full-panel image per device shape
# ---------------------------------------------------------------------------

def hex_rgb(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    if len(c) != 6:
        raise PackError(f"background must look like #1e1e2e, got {color!r}")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def panel_images(strip, spec: dict) -> dict:
    """Return the full-panel image of every device shape in `spec["shapes"]`."""
    from PIL import Image, ImageDraw, ImageFont
    pw, ph = spec["panel"]
    cw, ch = spec["cell"]
    cx, cy = spec["cell_xy"]
    shapes = spec["shapes"]
    if strip.size[0] < cw * len(shapes) or strip.size[1] < ch:
        raise PackError(f"the strip is {strip.size[0]}x{strip.size[1]}; {len(shapes)} cells of {cw}x{ch} "
                        f"need {cw * len(shapes)}x{ch}")
    if cx < 0 or cy < 0 or cx + cw > pw or cy + ch > ph:
        raise PackError(f"a {cw}x{ch} cell at ({cx}, {cy}) does not fit the {pw}x{ph} panel")
    images = {}
    if PIXEL_FORMATS[spec["pixel_format"]] == PIX_MONO_VPAGE:
        gray = strip.convert("L")
        for k, shape in enumerate(shapes):
            panel = Image.new("L", (pw, ph), 0)
            panel.paste(gray.crop((k * cw, 0, (k + 1) * cw, ch)), (cx, cy))
            images[shape] = panel
        return images
    bg = hex_rgb(spec["background"])
    sheet = strip.convert("RGBA")
    caption = spec.get("caption")
    for k, shape in enumerate(shapes):
        tile = sheet.crop((k * cw, 0, (k + 1) * cw, ch))
        flat = Image.alpha_composite(Image.new("RGBA", tile.size, bg + (255,)), tile).convert("RGB")
        panel = Image.new("RGB", (pw, ph), bg)
        panel.paste(flat, (cx, cy))
        if caption:
            d = ImageDraw.Draw(panel)
            font = ImageFont.load_default()
            y = int(spec.get("caption_y", cy + ch + 8))
            tw = d.textlength(caption, font=font)
            d.text(((pw - tw) // 2, y), caption, fill=CAPTION_INK, font=font)
            d.line([(pw - 40) // 2, y + 16, (pw + 40) // 2, y + 16], fill=CAPTION_RULE)
        images[shape] = rgb565_to_rgb(panel)
    return images


def moving_box(images: dict, mono: bool) -> tuple[int, int, int, int]:
    """Return the smallest box that holds every pixel that differs between two shapes.

    For a 1-bit panel the box grows outward to multiples of 8.
    """
    from PIL import ImageChops
    items = list(images.values())
    first = items[0].convert("RGB")
    box = None
    for other in items[1:]:
        b = ImageChops.difference(first, other.convert("RGB")).getbbox()
        if b is None:
            continue
        box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    if box is None:
        raise PackError("all mouth shapes are the same image")
    x0, y0, x1, y1 = box
    if mono:
        x0, y0 = x0 // 8 * 8, y0 // 8 * 8
        x1, y1 = -(-x1 // 8) * 8, -(-y1 // 8) * 8
    return x0, y0, x1 - x0, y1 - y0


def check_spec(spec: dict) -> dict:
    """Fill the defaults of a panel description and check it. Return a copy."""
    spec = dict(spec)
    if "shape_map" not in spec and "full_to_oled" in spec:
        spec["shape_map"] = spec["full_to_oled"]
    if "mouth_box" not in spec:
        spec["mouth_box"] = "auto"
    for key in ("panel", "pixel_format", "shapes"):
        if key not in spec:
            raise PackError(f"the panel description has no {key!r}")
    if spec["pixel_format"] not in PIXEL_FORMATS:
        raise PackError(f"unknown pixel format {spec['pixel_format']!r}; choose mono_vpage or rgb565_be")
    spec.setdefault("panel_fps", 60)
    spec.setdefault("cell", list(spec["panel"]))
    spec.setdefault("cell_xy", [0, 0])
    spec.setdefault("shape_map", {s: s for s in spec["shapes"]})
    spec.setdefault("closed_shapes", [spec["shapes"][0]])
    spec.setdefault("base_shape", spec["closed_shapes"][0])
    spec.setdefault("about", f"{spec['panel'][0]}x{spec['panel'][1]} {spec['pixel_format']}")
    known = set(spec["shapes"])
    for name in list(spec["closed_shapes"]) + [spec["base_shape"]] + list(spec["shape_map"].values()):
        if name not in known:
            raise PackError(f"{name!r} is not one of the strip's shapes: {', '.join(spec['shapes'])}")
    pw, ph = spec["panel"]
    mono = PIXEL_FORMATS[spec["pixel_format"]] == PIX_MONO_VPAGE
    if mono and (pw % 8 or ph % 8):
        raise PackError(f"a 1-bit panel must be a multiple of 8 on each side, got {pw}x{ph}")
    if spec["mouth_box"] != "auto":
        x, y, w, h = spec["mouth_box"]
        if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > pw or y + h > ph:
            raise PackError(f"mouth box {spec['mouth_box']} does not fit the {pw}x{ph} panel")
        if mono and any(v % 8 for v in (x, y, w, h)):
            raise PackError(f"on a 1-bit panel every value of the mouth box is a multiple of 8, got {spec['mouth_box']}")
    return spec


# ---------------------------------------------------------------------------
# The frame plan as runs in audio samples
# ---------------------------------------------------------------------------

# A mouth shape that a pause cuts shorter than this joins its neighbor:
# two panel frames at 60 Hz.
MIN_RUN = 1 / 30


def plan_runs(frames: list[str], fps: float, shape_map: dict[str, str], n_samples: int, rate: int,
              silences: list[list[float]] | None = None, closed: str | None = None) -> list[tuple[str, int]]:
    """Frame list at `fps` -> runs of (device shape, duration in samples).

    Plan frame k starts at sample round(k * rate / fps). Neighbors that map
    to the same device shape join into one run. The last run ends at the
    end of the audio.

    The frame list has one shape per 1/fps second, so a pause can begin up
    to one plan frame before the mouth closes. A panel refreshes faster than
    the plan and would show that. So each silent stretch of the audio
    (`silences`, in seconds) is cut into the runs at sample accuracy: the
    mouth shows `closed` for the whole stretch. A shape that the cut leaves
    shorter than MIN_RUN joins the shape before it, or else the pause.
    """
    spans: list[list] = []  # [start, end, shape]
    for k, shape in enumerate(frames):
        dev = shape_map[shape]
        start = min(n_samples, round(k * rate / fps))
        end = min(n_samples, round((k + 1) * rate / fps)) if k + 1 < len(frames) else n_samples
        if end <= start:
            continue
        if spans and spans[-1][2] == dev:
            spans[-1][1] = end
        else:
            spans.append([start, end, dev])
    spans[-1][1] = n_samples
    original = {(s, e) for s, e, _ in spans}

    for s_sec, e_sec in silences or []:
        s, e = max(0, round(s_sec * rate)), min(n_samples, round(e_sec * rate))
        cut: list[list] = []
        for a, b, shape in spans:
            if b <= s or a >= e or shape == closed:
                cut.append([a, b, shape])
                continue
            if a < s:
                cut.append([a, s, shape])
            cut.append([max(a, s), min(b, e), closed])
            if b > e:
                cut.append([e, b, shape])
        spans = cut

    def join(items: list[list]) -> list[list]:
        out: list[list] = []
        for a, b, shape in items:
            if out and out[-1][2] == shape:
                out[-1][1] = b
            else:
                out.append([a, b, shape])
        return out

    spans = join(spans)
    short = round(MIN_RUN * rate)
    i = 0
    while i < len(spans):
        a, b, shape = spans[i]
        if shape != closed and b - a < short and (a, b) not in original:
            if i > 0 and spans[i - 1][2] != closed:
                spans[i][2] = spans[i - 1][2]
            elif i + 1 < len(spans) and spans[i + 1][2] != closed:
                spans[i][2] = spans[i + 1][2]
            else:
                spans[i][2] = closed
            spans = join(spans)
            i = 0
            continue
        i += 1
    return [(shape, b - a) for a, b, shape in spans]


# ---------------------------------------------------------------------------
# The pack
# ---------------------------------------------------------------------------

def assemble_pack(pixel_format: int, panel: tuple[int, int], mouth: tuple[int, int, int, int], base_blob: bytes,
                  frame_blobs: list[bytes], runs: list[list[int]], closed_mask: int, rate: int,
                  pcm, audio: str = "adpcm") -> tuple[bytes, dict]:
    """Lay out the bytes of a pack. `runs` is a list of [frame index, samples].

    The base image covers the whole panel. `pcm` is any sequence of int16
    samples. Returns (pack, sizes by part).
    """
    n = len(pcm)
    if sum(d for _, d in runs) != n:
        raise PackError("the runs must cover the audio exactly")
    if not 1 <= len(frame_blobs) <= MAX_FRAMES:
        raise PackError(f"{len(frame_blobs)} frames; a pack holds 1 to {MAX_FRAMES}")
    run_bytes = bytearray()
    n_runs = 0
    for i, dur in runs:
        while dur > 0:  # a run field holds 24 bits
            part = min(dur, 0xFFFFFF)
            run_bytes += bytes([i]) + part.to_bytes(3, "little")
            dur -= part
            n_runs += 1
    if audio == "adpcm":
        audio_format, block, audio_blob = AUDIO_IMA_ADPCM, ADPCM_BLOCK, adpcm_encode(pcm)
    elif audio == "pcm16":
        audio_format, block, audio_blob = AUDIO_PCM16, 0, struct.pack(f"<{n}h", *[int(v) for v in pcm])
    elif audio == "none":
        audio_format, block, audio_blob = AUDIO_NONE, 0, b""
    else:
        raise PackError(f"unknown audio format {audio!r}; choose adpcm, pcm16, or none")
    frames_blob = b"".join(frame_blobs)
    base_off = HEADER_SIZE
    frames_off = base_off + len(base_blob)
    runs_off = frames_off + len(frames_blob)
    audio_off = runs_off + len(run_bytes)
    pw, ph = panel
    header = struct.pack(
        HEADER_FORMAT,
        b"PNPK", 1, pixel_format, audio_format, len(frame_blobs),
        pw, ph, 0, 0, pw, ph, *mouth,
        rate, n, n_runs, block, closed_mask,
        base_off, frames_off, runs_off, audio_off, len(audio_blob))
    assert len(header) == HEADER_SIZE
    data = header + base_blob + frames_blob + bytes(run_bytes) + audio_blob
    sizes = {"total": len(data), "header": HEADER_SIZE, "base": len(base_blob), "frames": len(frames_blob),
             "runs": len(run_bytes), "audio": len(audio_blob)}
    return data, sizes


def read_header(data: bytes) -> dict:
    """Parse the 64-byte header of a pack."""
    if len(data) < HEADER_SIZE or data[:4] != b"PNPK":
        raise PackError("not a pack: no PNPK magic")
    f = struct.unpack_from(HEADER_FORMAT, data)
    return {"version": f[1], "pixel_format": f[2], "audio_format": f[3], "frame_count": f[4],
            "panel": [f[5], f[6]], "base": list(f[7:11]), "mouth": list(f[11:15]),
            "sample_rate": f[15], "sample_count": f[16], "run_count": f[17], "adpcm_block": f[18],
            "closed_mask": f[19], "base_off": f[20], "frames_off": f[21], "runs_off": f[22],
            "audio_off": f[23], "audio_bytes": f[24]}


def build_pack(plan: dict, pcm, strip, spec: dict, rate: int = DEFAULT_RATE,
               audio: str = "adpcm") -> tuple[bytes, dict]:
    """Return (pack bytes, description) for a plan, its samples at `rate`, and the art."""
    spec = dict(spec)
    spec.setdefault("background", plan.get("background", "#000000"))
    spec = check_spec(spec)
    pixel_format = PIXEL_FORMATS[spec["pixel_format"]]
    encode = ENCODERS[pixel_format]
    pw, ph = spec["panel"]
    images = panel_images(strip, spec)
    shape_map = spec["shape_map"]
    missing = sorted(set(plan["frames"]) - set(shape_map))
    if missing:
        raise PackError(f"the shape map has no entry for the plan's shapes: {', '.join(missing)}")
    if spec["mouth_box"] == "auto":
        mx, my, mw, mh = moving_box(images, pixel_format == PIX_MONO_VPAGE)
        if mw * mh > pw * ph // 2:
            print(f"warning: the shapes differ over a {mw}x{mh} box, more than half the panel. "
                  "Clean the sheet so that only the mouth changes.", file=sys.stderr)
    else:
        mx, my, mw, mh = spec["mouth_box"]

    n = len(pcm)
    if n == 0:
        raise PackError("the audio is empty")
    base_shape = spec["base_shape"]
    runs = plan_runs(plan["frames"], plan["fps"], shape_map, n, rate, plan.get("silences"), base_shape)

    # One frame per distinct mouth image that the plan or the base uses.
    names: list[str] = []
    blobs: list[bytes] = []
    index_of: dict[str, int] = {}
    for shape in [base_shape] + [s for s, _ in runs]:
        if shape in index_of:
            continue
        blob = encode(images[shape].crop((mx, my, mx + mw, my + mh)))
        if blob in blobs:
            index_of[shape] = blobs.index(blob)
            names[index_of[shape]] += "+" + shape
        else:
            index_of[shape] = len(blobs)
            blobs.append(blob)
            names.append(shape)
    if len(blobs) > MAX_FRAMES:
        raise PackError(f"{len(blobs)} frames; a pack holds at most {MAX_FRAMES}")
    closed_mask = 0
    for shape, i in index_of.items():
        if shape in spec["closed_shapes"]:
            closed_mask |= 1 << i

    # Join runs that ended up on the same frame.
    merged: list[list[int]] = []
    for shape, dur in runs:
        i = index_of[shape]
        if merged and merged[-1][0] == i:
            merged[-1][1] += dur
        else:
            merged.append([i, dur])
    base_blob = encode(images[base_shape])
    data, sizes = assemble_pack(pixel_format, (pw, ph), (mx, my, mw, mh), base_blob, blobs,
                                merged, closed_mask, rate, pcm, audio)

    t, run_list = 0, []
    for i, dur in merged:
        run_list.append([t, i])
        t += dur
    info = {
        "target": spec.get("target", "custom"), "about": spec["about"], "panel": [pw, ph],
        "panel_fps": spec["panel_fps"], "pixel_format": spec["pixel_format"],
        "text": plan.get("text", ""),
        "sample_rate": rate, "sample_count": n, "duration": n / rate,
        "audio_format": audio, "mouth": [mx, my, mw, mh],
        "frames": names, "closed_frames": [i for i in range(len(blobs)) if closed_mask >> i & 1],
        "shape_map": shape_map,
        "runs": run_list,  # [start sample, frame index]
        "bytes": sizes,
    }
    for key in ("character", "mood"):
        if key in plan:
            info[key] = plan[key]
    return data, info


def write_pack(out: Path, data: bytes, info: dict) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    Path(str(out) + ".json").write_text(json.dumps(info) + "\n")


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def _tone(n: int, rate: int) -> list[int]:
    return [int(12000 * math.sin(2 * math.pi * (200 + 900 * i / rate) * i / rate) * min(1, i / rate * 40))
            for i in range(n)]


def selftest() -> None:
    # ADPCM: the decoder gives back the encoder's own predictions, and the
    # error stays small on a rising tone.
    pcm = _tone(1200, 8000)
    enc = adpcm_encode(pcm)
    assert len(enc) == 3 * ADPCM_BLOCK, len(enc)
    dec = adpcm_decode(enc, len(pcm))
    assert dec[0] == pcm[0] and dec[505] == pcm[505]
    assert max(abs(a - b) for a, b in zip(pcm, dec)) < 2500

    # Runs: neighbors join, a silence is cut in at sample accuracy, and the
    # sliver that the cut leaves joins the shape before it.
    ident = {s: s for s in ("rest", "wide", "smile")}
    frames = ["rest"] * 2 + ["wide"] * 4 + ["smile"] * 2 + ["rest"] * 2
    runs = plan_runs(frames, 10, ident, 16000, 16000)
    assert runs == [("rest", 3200), ("wide", 6400), ("smile", 3200), ("rest", 3200)], runs
    # The silence 0.55 to 0.79 s closes the mouth from sample 8800, not from
    # the plan frame at 9600. It leaves 10 ms of "smile" (under MIN_RUN)
    # between two closed runs, and the pause takes that too.
    runs = plan_runs(frames, 10, ident, 16000, 16000, [[0.55, 0.79]], "rest")
    assert runs == [("rest", 3200), ("wide", 5600), ("rest", 7200)], runs
    # A silence that ends 100 ms before the plan's own change keeps "smile".
    runs = plan_runs(frames, 10, ident, 16000, 16000, [[0.55, 0.70]], "rest")
    assert runs == [("rest", 3200), ("wide", 5600), ("rest", 2400), ("smile", 1600), ("rest", 3200)], runs

    # Byte layout: a hand-made pack reads back field by field.
    base = bytes(range(1, 33))
    blobs = [bytes([i * 16 + c for c in range(8)]) for i in (1, 2, 3)]
    data, sizes = assemble_pack(PIX_MONO_VPAGE, (16, 16), (8, 8, 8, 8), base, blobs,
                                [[0, 200], [1, 333], [2, 67], [1, 400], [0, 200]], 0b001, 8000, pcm)
    h = read_header(data)
    assert h["panel"] == [16, 16] and h["mouth"] == [8, 8, 8, 8] and h["frame_count"] == 3
    assert h["sample_count"] == 1200 and h["run_count"] == 5 and h["closed_mask"] == 1
    assert h["adpcm_block"] == 256 and h["audio_bytes"] == 768 and sizes["total"] == len(data)
    assert data[h["runs_off"]:h["runs_off"] + 4] == bytes([0, 200, 0, 0])
    assert adpcm_decode(data[h["audio_off"]:], 1200) == dec
    try:
        assemble_pack(PIX_MONO_VPAGE, (16, 16), (8, 8, 8, 8), base, blobs, [[0, 100]], 1, 8000, pcm)
        raise AssertionError("runs that do not cover the audio must fail")
    except PackError:
        pass

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("selftest OK: device_pack (audio, runs, layout; image tests skipped: pillow is missing)")
        return

    # 1-bit: a 3-cell strip of 16x16 panels; the mouth is the lower right tile.
    strip = Image.new("1", (48, 16), 0)
    d = ImageDraw.Draw(strip)
    for k in range(3):
        d.rectangle([k * 16, 0, k * 16 + 15, 15], fill=1)
        d.rectangle([k * 16 + 9, 9, k * 16 + 10 + 2 * k, 10 + k], fill=0)
    spec = {"panel": [16, 16], "pixel_format": "mono_vpage", "shapes": ["shut", "half", "full"],
            "closed_shapes": ["shut"], "shape_map": {"rest": "shut", "wide": "full", "smile": "half"},
            "mouth_box": "auto"}
    plan = {"fps": 10, "frames": frames, "silences": [], "text": "t"}
    data, info = build_pack(plan, _tone(16000, 16000), strip, spec, 16000)
    h = read_header(data)
    assert info["mouth"] == [8, 8, 8, 8] == h["mouth"], info["mouth"]
    assert info["frames"] == ["shut", "full", "half"] and info["closed_frames"] == [0], info
    assert info["runs"] == [[0, 0], [3200, 1], [9600, 2], [12800, 0]], info["runs"]
    assert h["base_off"] == 64 and h["frames_off"] == 64 + 32 and h["runs_off"] == 64 + 32 + 24
    # Column 9 of the "shut" cell: rows 9 and 10 are dark, so bits 1 and 2 are 0.
    assert data[h["frames_off"] + 1] == 0xFF & ~0b110, data[h["frames_off"] + 1]
    assert mono_vpage(strip.crop((0, 0, 16, 16)))[:16] == b"\xff" * 16
    try:
        build_pack(plan, _tone(16000, 16000), strip, {**spec, "mouth_box": [8, 8, 8, 6]}, 16000)
        raise AssertionError("a mouth box off the 8-pixel grid must fail")
    except PackError:
        pass

    # RGB565: a 3-cell sheet of 8x8 at (2, 4) on a 12x16 panel; two shapes
    # with the same mouth share one frame.
    sheet = Image.new("RGBA", (24, 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(sheet)
    for k in range(3):
        d.rectangle([k * 8 + 1, 1, k * 8 + 6, 6], fill=(200, 120, 40, 255))
    d.rectangle([8 + 3, 4, 8 + 5, 5], fill=(255, 255, 255, 255))
    spec = {"panel": [12, 16], "pixel_format": "rgb565_be", "cell": [8, 8], "cell_xy": [2, 4],
            "shapes": ["rest", "wide", "smile"], "closed_shapes": ["rest", "smile"], "base_shape": "rest"}
    data, info = build_pack({**plan, "background": "#1e1e2e"}, _tone(16000, 16000), sheet, spec, 16000, "pcm16")
    h = read_header(data)
    assert info["mouth"] == [5, 8, 3, 2], info["mouth"]
    assert info["frames"] == ["rest+smile", "wide"] and info["closed_frames"] == [0], info
    assert h["audio_bytes"] == 32000 and h["adpcm_block"] == 0
    # The first base pixel is the background, as RGB565 high byte first.
    r, g, b = 0x1E, 0x1E, 0x2E
    v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
    assert data[64:66] == bytes([v >> 8, v & 255])
    assert rgb565_to_rgb(Image.new("RGB", (1, 1), (255, 255, 255))).getpixel((0, 0)) == (255, 255, 255)
    assert rgb565_to_rgb(Image.new("RGB", (1, 1), (30, 30, 46))).getpixel((0, 0)) == (24, 28, 41)

    # The presets are complete and consistent.
    for name, preset in PRESETS.items():
        s = check_spec({**preset, "background": "#000000"})
        assert set(s["shape_map"]) == set(SHAPES), name
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "a" / "line.pnpk"
        write_pack(out, data, info)
        assert out.read_bytes() == data and json.loads(Path(str(out) + ".json").read_text())["bytes"]["total"] == len(data)
    print("selftest OK: device_pack")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _ints(text: str, n: int, what: str) -> list[int]:
    parts = text.replace("x", ",").split(",")
    if len(parts) != n:
        raise PackError(f"{what} takes {n} numbers, got {text!r}")
    return [int(p) for p in parts]


def spec_from_args(a: argparse.Namespace) -> dict:
    """Build the panel description: the preset or the file, then the single options."""
    if a.panel_file:
        spec = json.loads(a.panel_file.read_text())
        if a.target:
            spec = {**PRESETS[a.target], **spec, "target": a.target}
    elif a.target:
        spec = {**PRESETS[a.target], "target": a.target}
    else:
        raise PackError("give --target or --panel-file")
    if a.panel:
        spec["panel"] = _ints(a.panel, 2, "--panel")
    if a.pixel_format:
        spec["pixel_format"] = a.pixel_format
    if a.panel_fps:
        spec["panel_fps"] = a.panel_fps
    if a.cell:
        spec["cell"] = _ints(a.cell, 2, "--cell")
    if a.cell_xy:
        spec["cell_xy"] = _ints(a.cell_xy, 2, "--cell-xy")
    if a.shapes:
        spec["shapes"] = [s.strip() for s in a.shapes.split(",")]
    if a.shape_map:
        spec["shape_map"] = json.loads(a.shape_map.read_text())
    if a.closed:
        spec["closed_shapes"] = [s.strip() for s in a.closed.split(",")]
    if a.base_shape:
        spec["base_shape"] = a.base_shape
    if a.mouth_box:
        spec["mouth_box"] = "auto" if a.mouth_box == "auto" else _ints(a.mouth_box, 4, "--mouth-box")
    if a.background:
        spec["background"] = a.background
    if a.caption:
        spec["caption"] = a.caption
    if a.caption_y is not None:
        spec["caption_y"] = a.caption_y
    return spec


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Export a device pack (.pnpk) from a frame plan, a WAV, and an art strip.")
    ap.add_argument("--plan", type=Path, help="plan file from viseme_plan.py (or a .timeline.json)")
    ap.add_argument("--wav", type=Path, help="audio of the line")
    ap.add_argument("--strip", type=Path, help="art strip PNG, one cell per device shape")
    ap.add_argument("--target", choices=sorted(PRESETS), help="preset panel description")
    ap.add_argument("--panel-file", type=Path, help="panel description (JSON); replaces or extends the preset")
    ap.add_argument("--out", type=Path, help="pack to write; <out>.json is written next to it")
    ap.add_argument("--rate", type=int, default=DEFAULT_RATE, help="audio sample rate in Hz (default 16000)")
    ap.add_argument("--audio", choices=["adpcm", "pcm16", "none"], default="adpcm")
    ap.add_argument("--panel", help="panel size, WxH")
    ap.add_argument("--pixel-format", choices=sorted(PIXEL_FORMATS))
    ap.add_argument("--panel-fps", type=int, help="panel frames per second for the simulator (default 60)")
    ap.add_argument("--cell", help="size of one strip cell, WxH")
    ap.add_argument("--cell-xy", help="where the cell sits on the panel, X,Y")
    ap.add_argument("--shapes", help="cell names in strip order, comma-separated")
    ap.add_argument("--shape-map", type=Path, help="JSON file: plan shape -> device shape")
    ap.add_argument("--closed", help="device shapes with the lips together, comma-separated")
    ap.add_argument("--base-shape", help="device shape of the base image and of pauses")
    ap.add_argument("--mouth-box", help='X,Y,W,H on the panel, or "auto"')
    ap.add_argument("--background", help='color behind the cell, "#rrggbb" (default: the plan\'s)')
    ap.add_argument("--caption", help="text under the face (rgb565_be only)")
    ap.add_argument("--caption-y", type=int, help="top of the caption in panel pixels")
    ap.add_argument("--print-preset", choices=sorted(PRESETS), help="print a preset as JSON and exit")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    a = ap.parse_args(argv)

    if a.selftest:
        selftest()
        return 0
    if a.print_preset:
        print(json.dumps(PRESETS[a.print_preset], indent=1))
        return 0
    if not (a.plan and a.wav and a.strip and a.out):
        ap.error("--plan, --wav, --strip and --out are required")
    try:
        from PIL import Image
    except ImportError:
        print("error: Pillow is missing; run this script with `uv run`", file=sys.stderr)
        return 2
    try:
        spec = spec_from_args(a)
        plan = json.loads(a.plan.read_text())
        for key in ("fps", "frames"):
            if key not in plan:
                raise PackError(f"{a.plan}: not a plan file (no {key!r})")
        strip = Image.open(a.strip)
        strip.load()
        pcm = load_audio(a.wav, a.rate)
        data, info = build_pack(plan, pcm, strip, spec, a.rate, a.audio)
        write_pack(a.out, data, info)
    except (OSError, ValueError, KeyError, PackError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    b = info["bytes"]
    print(f"{a.out}  {b['total']} bytes: base {b['base']}, {len(info['frames'])} frames {b['frames']}, "
          f"{len(info['runs'])} runs {b['runs']}, audio {b['audio']} ({info['audio_format']}, "
          f"{info['sample_rate']} Hz, {info['duration']:.2f} s), mouth box {info['mouth']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
