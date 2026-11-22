#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Render a mouth-shape plan as an MP4 file, and optionally as a web player.

Needs `ffmpeg` and `ffprobe` on PATH; no Python packages.

Inputs: `--sheet sheet.png` (a horizontal strip, one square cell per shape, in
the order of the plan's `shapes`), `--plan plan.json` (from `viseme_plan.py`)
and `--wav audio.wav`. Output: `--out clip.mp4`, an H.264 video with the
audio, and with `--web DIR` a static player (`index.html`, `player.js`,
`sheet.png`, `audio.wav`, `timeline.json` = the plan) that picks the frame
from `audio.currentTime`, so the mouth cannot drift from the sound.

ffmpeg cuts each cell from the sheet, composites it over the background color
and scales it by a whole number with nearest neighbor, so that every art pixel
stays a sharp square. The video has exactly one frame per entry of the plan's
`frames` at a constant frame rate, so frame k is on screen from k/fps to
(k+1)/fps of the audio.

Usage:
    uv run render_clip.py --sheet sheet.png --plan plan.json --wav audio.wav \\
        --out clip.mp4 [--scale 4] [--web player/]
    uv run render_clip.py --selftest
Exit code 0 on success; non-zero with a one-line reason on failure.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

PLAYER_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lip-sync player</title>
<style>
  :root { --bg: #14121c; --panel: #1e1b2b; --ink: #ece7f5; --dim: #9a93ad; --accent: #f2c14e; }
  * { box-sizing: border-box; }
  body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: var(--bg);
         color: var(--ink); font: 15px/1.5 ui-monospace, "SF Mono", Menlo, monospace; padding: 16px; }
  main { width: min(100%, 560px); display: grid; gap: 14px; }
  canvas { width: 100%; aspect-ratio: 1; image-rendering: pixelated; border: 4px solid #000;
           box-shadow: 0 0 0 4px var(--panel); background: var(--panel); }
  audio { width: 100%; }
  .row { display: flex; justify-content: space-between; gap: 12px; color: var(--dim); font-size: 13px; }
  .row b { color: var(--accent); font-weight: 600; }
  p { margin: 0; color: var(--dim); font-size: 13px; }
</style>
</head>
<body>
<main>
  <canvas id="stage" width="128" height="128" aria-label="Narrating character"></canvas>
  <audio id="audio" src="audio.wav" controls preload="auto"></audio>
  <div class="row"><span id="who"></span><span>frame <b id="frame">0</b> · <b id="shape">rest</b></span></div>
  <p id="text"></p>
</main>
<script src="player.js"></script>
</body>
</html>
"""

PLAYER_JS = r"""// Lip-sync web player.
//
// The mouth frame comes from audio.currentTime on every animation frame:
//   frame index = floor(currentTime * fps)
// The page never runs its own clock, so the mouth cannot drift from the
// sound, and seeking or pausing the audio moves the mouth with it.

const canvas = document.getElementById("stage");
const ctx = canvas.getContext("2d");
const audio = document.getElementById("audio");
const out = { frame: document.getElementById("frame"), shape: document.getElementById("shape") };

let timeline = null;
let sheet = null;
let shown = null;

// Return the mouth shape for a time in seconds.
function shapeAt(t) {
  const frames = timeline.frames;
  const k = Math.min(frames.length - 1, Math.max(0, Math.floor(t * timeline.fps)));
  return { k, shape: frames[k] };
}

function draw(shape) {
  const cell = timeline.cell;
  const col = timeline.shapes.indexOf(shape);
  ctx.imageSmoothingEnabled = false;
  ctx.fillStyle = timeline.background;
  ctx.fillRect(0, 0, cell, cell);
  ctx.drawImage(sheet, col * cell, 0, cell, cell, 0, 0, cell, cell);
}

function tick() {
  // After the audio ends, show the first frame's shape (the mouth at rest).
  const { k, shape } = audio.ended ? { k: 0, shape: timeline.frames[0] } : shapeAt(audio.currentTime);
  if (shape !== shown) {
    draw(shape);
    shown = shape;
    out.shape.textContent = shape;
  }
  out.frame.textContent = k;
  requestAnimationFrame(tick);
}

async function start() {
  timeline = await (await fetch("timeline.json")).json();
  sheet = new Image();
  sheet.src = "sheet.png";
  await sheet.decode();
  canvas.width = canvas.height = timeline.cell;
  document.getElementById("who").textContent = `${timeline.fps} fps`;
  document.getElementById("text").textContent = timeline.text || "";
  // Tests read these to compare the drawn frame with the timeline.
  window.narrator = { timeline, shapeAt, current: () => shown };
  tick();
}

start();
"""


def run(cmd: list[str]) -> bytes:
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {proc.stderr.decode(errors='replace').strip()[-300:]}")
    return proc.stdout


def write_tiles(sheet: Path, plan: dict, scale: int, tmp: Path) -> dict[str, Path]:
    """Have ffmpeg cut each cell, composite it over the background, scale it, and save a PNG."""
    cell = int(plan["cell"])
    size = cell * scale
    bg = "0x" + plan["background"].lstrip("#")
    tiles: dict[str, Path] = {}
    for k, shape in enumerate(plan["shapes"]):
        path = tmp / f"tile_{k:02d}.png"
        # The color source sits inside the graph and is forced to rgba, so that
        # the background color does not take a round trip through YUV.
        graph = (
            f"color=c={bg}:s={cell}x{cell},format=rgba[bg];"
            f"[0:v]crop={cell}:{cell}:{k * cell}:0,format=rgba[fg];"
            f"[bg][fg]overlay=format=rgb:shortest=1,"
            f"scale={size}:{size}:flags=neighbor,format=rgb24"
        )
        run(["ffmpeg", "-v", "error", "-y", "-i", str(sheet), "-filter_complex", graph,
             "-frames:v", "1", str(path)])
        tiles[shape] = path
    return tiles


def render_mp4(sheet: Path, plan: dict, wav: Path, out: Path, scale: int) -> int:
    """Encode the plan's frames and the audio into an H.264 MP4. Return the frame count."""
    frames = plan["frames"]
    fps = int(plan["fps"])
    size = int(plan["cell"]) * scale
    if size % 2:
        raise RuntimeError(f"video size {size} is odd; H.264 needs an even size (change --scale)")
    unknown = sorted(set(frames) - set(plan["shapes"]))
    if unknown:
        raise RuntimeError(f"plan uses shapes that are not in its shape list: {', '.join(unknown)}")
    with tempfile.TemporaryDirectory(prefix="render-") as tmp_name:
        tmp = Path(tmp_name)
        tiles = write_tiles(sheet, plan, scale, tmp)
        # One numbered file per video frame, linked to its tile: ffmpeg then reads
        # exactly len(frames) frames at a constant rate.
        seq = tmp / "seq"
        seq.mkdir()
        for k, shape in enumerate(frames):
            link = seq / f"f{k:06d}.png"
            try:
                os.symlink(tiles[shape], link)
            except OSError:
                shutil.copyfile(tiles[shape], link)
        out.parent.mkdir(parents=True, exist_ok=True)
        run(["ffmpeg", "-y", "-loglevel", "error",
             "-framerate", str(fps), "-i", str(seq / "f%06d.png"),
             "-i", str(wav),
             "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-tune", "animation",
             "-pix_fmt", "yuv420p", "-r", str(fps),
             "-c:a", "aac", "-b:a", "192k",
             "-movflags", "+faststart",
             str(out)])
    return len(frames)


def export_web(out_dir: Path, sheet: Path, wav: Path, plan: dict) -> None:
    """Write a static web player: the page, the script, the sheet, the audio, the plan."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(PLAYER_HTML)
    (out_dir / "player.js").write_text(PLAYER_JS)
    shutil.copyfile(sheet, out_dir / "sheet.png")
    shutil.copyfile(wav, out_dir / "audio.wav")
    (out_dir / "timeline.json").write_text(json.dumps(plan, indent=1) + "\n")


def probe(mp4: Path) -> dict:
    """Return width, height, fps, decoded frame count and whether an audio stream exists."""
    v = json.loads(run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames",
                        "-of", "json", str(mp4)]))["streams"][0]
    a = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
                        "stream=codec_name", "-of", "json", str(mp4)]))["streams"]
    num, den = v["r_frame_rate"].split("/")
    return {"width": int(v["width"]), "height": int(v["height"]), "fps": int(num) / int(den),
            "frames": int(v["nb_read_frames"]), "audio": [s["codec_name"] for s in a]}


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def _png(path: Path, w: int, h: int, rgba: bytes) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    rows = b"".join(b"\x00" + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def selftest() -> None:
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        print("SKIP: rendering needs ffmpeg and ffprobe")
        return
    import math
    import wave
    shapes = ["rest", "closed", "small_open", "medium_open", "wide_open", "smile",
              "round_small", "pucker", "teeth", "hiss", "tongue", "jaw_drop"]
    cell, scale = 16, 4
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        # A sheet with 12 flat-colored cells; the first has a transparent corner.
        px = bytearray()
        for y in range(cell):
            for k in range(12):
                for x in range(cell):
                    px += bytes((0, 0, 0, 0)) if (k == 0 and x < 4 and y < 4) else bytes((20 * k, 255 - 20 * k, 90, 255))
        sheet = tmp / "sheet.png"
        _png(sheet, cell * 12, cell, bytes(px))
        wav = tmp / "a.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * 220 * i / 16000)))
                                   for i in range(17600)))
        # 17 frames at 15 fps: a count that is not a whole number of seconds.
        frames = (["rest"] * 3 + ["closed"] * 2 + ["wide_open"] * 5 + ["smile"] * 4 + ["rest"] * 3)
        plan = {"fps": 15, "duration": 1.1, "cell": cell, "background": "#1e1e2e", "shapes": shapes,
                "closed_shapes": ["closed", "rest"], "frames": frames, "text": "t"}
        out = tmp / "clip.mp4"
        n = render_mp4(sheet, plan, wav, out, scale)
        info = probe(out)
        assert n == 17 and info["frames"] == 17, info
        assert info["fps"] == 15.0, info
        assert (info["width"], info["height"]) == (64, 64), info
        assert info["audio"], "no audio stream"
        web = tmp / "web"
        export_web(web, sheet, wav, plan)
        names = sorted(p.name for p in web.iterdir())
        assert names == ["audio.wav", "index.html", "player.js", "sheet.png", "timeline.json"], names
        html = (web / "index.html").read_text()
        assert 'name="viewport"' in html and "image-rendering: pixelated" in html and 'src="audio.wav"' in html
        assert "currentTime" in (web / "player.js").read_text()
    print("selftest OK: render_clip")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render a mouth-shape plan as an MP4 and an optional web player.")
    ap.add_argument("--sheet", type=Path, help="sprite sheet PNG (one cell per shape)")
    ap.add_argument("--plan", type=Path, help="plan file from viseme_plan.py")
    ap.add_argument("--wav", type=Path, help="audio file")
    ap.add_argument("--out", type=Path, help="MP4 to write")
    ap.add_argument("--scale", type=int, default=4, help="whole-number pixel scale (default 4: 128 -> 512 px)")
    ap.add_argument("--web", type=Path, help="also write a static web player to this folder")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    a = ap.parse_args(argv)
    if a.selftest:
        selftest()
        return 0
    if not (a.sheet and a.plan and a.wav and a.out):
        ap.error("--sheet, --plan, --wav and --out are required")
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        print("error: ffmpeg and ffprobe must be on PATH", file=sys.stderr)
        return 2
    try:
        plan = json.loads(a.plan.read_text())
        n = render_mp4(a.sheet, plan, a.wav, a.out, a.scale)
        if a.web:
            export_web(a.web, a.sheet, a.wav, plan)
    except (OSError, RuntimeError, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"{a.out}  {n} frames at {plan['fps']} fps, {int(plan['cell']) * a.scale}x{int(plan['cell']) * a.scale}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
