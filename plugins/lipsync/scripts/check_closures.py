#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Check 3: does every /p b m/ and every long pause show a closed mouth?

Needs `ffmpeg` and `ffprobe` on PATH; uses numpy when it is installed (faster)
and plain Python otherwise.

The check trusts neither the plan nor the renderer. It reads the finished MP4:

1. ffmpeg decodes every video frame. Each frame is matched to the nearest of
   the 12 mouth-shape tiles of the sprite sheet (ffmpeg cuts each cell from
   the sheet, composites it over the plan's background color and scales it by
   nearest neighbor to the video size). The check compares only the pixel
   positions where the tiles differ from each other, so it knows which shape
   is on screen at each moment, with its presentation time from the file.
2. The reference phones come from an INDEPENDENT forced alignment of the
   clip's audio (`align_mfa.py`), not from the plan's own phones.
3. A /p b m/ phoneme lands on a closed frame when at least one frame that is
   on screen during the phoneme shows a closed shape (one of the plan's
   `closed_shapes`, `rest` or `closed`). A pause longer than 150 ms lands on a
   closed frame when every frame that lies fully inside the pause shows a
   closed shape, and at least one such frame exists. `spn` (an unknown spoken
   word) is speech, not a pause.

Pass: the number of phonemes and pauses that miss is 0. Exit code 0 on pass,
1 on fail (the last line is `CHECK 3 PASS` or `CHECK 3 FAIL`).

Usage:
    uv run check_closures.py clip.mp4 --sheet sheet.png --plan plan.json \\
        --phones reference_phones.json [--out result.json]
    uv run check_closures.py --selftest
"""

from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path

LONG_PAUSE = 0.150
MAX_POSITIONS = 4000  # tile pixels that the frame classifier compares

BILABIALS = {"P", "B", "M"}
SILENCE_LABELS = {"", "sil", "sp", "<eps>", "SIL", "pau"}


def strip_stress(phone: str) -> str:
    return phone.rstrip("012").upper()


def is_silence(label: str) -> bool:
    return label.strip() in SILENCE_LABELS


@dataclass
class Phone:
    start: float
    end: float
    label: str

    @property
    def dur(self) -> float:
        return self.end - self.start


def normalize(phones: list[Phone], duration: float) -> list[Phone]:
    """Return phones that cover [0, duration] with no gaps or overlaps.

    Gaps become silence, and neighboring silences join into one.
    """
    out: list[Phone] = []
    t = 0.0
    for p in sorted(phones, key=lambda p: p.start):
        start = max(p.start, t)
        end = min(p.end, duration)
        if end <= start:
            continue
        if start > t + 1e-6:
            out.append(Phone(t, start, "sil"))
        out.append(Phone(start, end, "sil" if is_silence(p.label) else p.label))
        t = end
    if t < duration - 1e-6:
        out.append(Phone(t, duration, "sil"))
    joined: list[Phone] = []
    for p in out:
        if joined and is_silence(p.label) and is_silence(joined[-1].label):
            joined[-1].end = p.end
        else:
            joined.append(p)
    return joined


# ---------------------------------------------------------------------------
# ffmpeg helpers
# ---------------------------------------------------------------------------

def run(cmd: list[str]) -> bytes:
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {proc.stderr.decode(errors='replace').strip()[-300:]}")
    return proc.stdout


def probe_video(mp4: Path) -> tuple[int, int, float, list[float]]:
    """Return (width, height, fps, presentation time of every frame)."""
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=width,height,r_frame_rate:frame=best_effort_timestamp_time",
               "-of", "json", str(mp4)])
    probe = json.loads(out)
    s = probe["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    times = [float(f["best_effort_timestamp_time"]) for f in probe["frames"]]
    return int(s["width"]), int(s["height"]), int(num) / int(den), times


def tile_rgb(sheet: Path, k: int, cell: int, background: str, w: int, h: int) -> bytes:
    """Cut cell k from the sheet, composite it over the background, scale it to w x h (rgb24)."""
    bg = "0x" + background.lstrip("#")
    # The color source sits inside the filter graph and is forced to rgba, so
    # that the background color does not take a round trip through YUV.
    graph = (
        f"color=c={bg}:s={cell}x{cell},format=rgba[bg];"
        f"[0:v]crop={cell}:{cell}:{k * cell}:0,format=rgba[fg];"
        f"[bg][fg]overlay=format=rgb:shortest=1,"
        f"scale={w}:{h}:flags=neighbor,format=rgb24"
    )
    raw = run(["ffmpeg", "-v", "error", "-i", str(sheet), "-filter_complex", graph,
               "-frames:v", "1", "-f", "rawvideo", "-"])
    if len(raw) != w * h * 3:
        raise RuntimeError(f"tile {k}: ffmpeg returned {len(raw)} bytes, expected {w * h * 3}")
    return raw


def build_tiles(sheet: Path, plan: dict, w: int, h: int) -> dict[str, bytes]:
    cell = int(plan["cell"])
    return {name: tile_rgb(sheet, k, cell, plan["background"], w, h)
            for k, name in enumerate(plan["shapes"])}


def sample_positions(tiles: dict[str, bytes], w: int, h: int, cell: int) -> list[int]:
    """Return byte offsets (of the red channel) where the tiles differ from each other.

    A tile is a nearest-neighbor scaling of a cell, so it is made of flat
    blocks. The check looks at the middle pixel of each block, which is far
    from the block edges where video compression smears colors. At most
    MAX_POSITIONS positions are kept, spread evenly.
    """
    vals = list(tiles.values())
    found: list[int] = []
    for cy in range(cell):
        y = min(h - 1, int((cy + 0.5) * h / cell))
        for cx in range(cell):
            x = min(w - 1, int((cx + 0.5) * w / cell))
            o = (y * w + x) * 3
            first = vals[0][o:o + 3]
            if any(v[o:o + 3] != first for v in vals[1:]):
                found.append(o)
    if len(found) > MAX_POSITIONS:
        step = len(found) / MAX_POSITIONS
        found = [found[int(i * step)] for i in range(MAX_POSITIONS)]
    return found


def classify_frames(mp4: Path, tiles: dict[str, bytes], positions: list[int], w: int, h: int) -> list[str]:
    """Stream the decoded frames and name the nearest tile for each."""
    names = list(tiles)
    idx = [o + c for o in positions for c in range(3)]
    try:
        import numpy as np
    except ImportError:
        np = None
    if np is not None:
        index = np.array(idx)
        refs = np.stack([np.frombuffer(tiles[n], np.uint8)[index].astype(np.int32) for n in names])
    else:
        refs_list = [[tiles[n][i] for i in idx] for n in names]
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(mp4), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                            stdout=subprocess.PIPE)
    size = w * h * 3
    out: list[str] = []
    cache: dict[bytes, str] = {}
    while True:
        buf = proc.stdout.read(size)
        while buf and len(buf) < size:
            more = proc.stdout.read(size - len(buf))
            if not more:
                break
            buf += more
        if len(buf) < size:
            break
        if np is not None:
            f = np.frombuffer(buf, np.uint8)[index].astype(np.int32)
            out.append(names[int(np.abs(refs - f).sum(1).argmin())])
            continue
        sample = bytes(buf[i] for i in idx)
        if sample not in cache:
            best, best_err = 0, None
            for n, ref in enumerate(refs_list):
                err = sum(abs(a - b) for a, b in zip(ref, sample))
                if best_err is None or err < best_err:
                    best, best_err = n, err
            cache[sample] = names[best]
        out.append(cache[sample])
    proc.stdout.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg could not decode the video")
    return out


# ---------------------------------------------------------------------------
# The check
# ---------------------------------------------------------------------------

def judge(shapes: list[str], times: list[float], fps: float, phones: list[Phone], closed: set) -> dict:
    """Apply the pass rule to the shape on screen in each frame."""
    spans = [(t, times[i + 1] if i + 1 < len(times) else t + 1 / fps) for i, t in enumerate(times)]
    misses, n_bilabial, n_pause = [], 0, 0
    for p in phones:
        if is_silence(p.label):
            if p.dur <= LONG_PAUSE:
                continue
            n_pause += 1
            inside = [i for i, (s, e) in enumerate(spans) if s >= p.start - 1e-6 and e <= p.end + 1e-6]
            ok = bool(inside) and all(shapes[i] in closed for i in inside)
            kind = "pause"
        elif strip_stress(p.label) in BILABIALS:
            n_bilabial += 1
            on = [i for i, (s, e) in enumerate(spans) if s < p.end and e > p.start]
            ok = any(shapes[i] in closed for i in on)
            inside = on
            kind = p.label
        else:
            continue  # includes "spn": speech of unknown shape, not a pause
        if not ok:
            misses.append({"kind": kind, "start": round(p.start, 3), "end": round(p.end, 3),
                           "frames": [[i, shapes[i]] for i in inside]})
    return {"bilabials": n_bilabial, "long_pauses": n_pause,
            "misses": len(misses), "missed": misses, "pass": not misses}


def check(mp4: Path, sheet: Path, plan: dict, ref: dict) -> dict:
    w, h, fps, times = probe_video(mp4)
    tiles = build_tiles(sheet, plan, w, h)
    positions = sample_positions(tiles, w, h, int(plan["cell"]))
    if not positions:
        raise RuntimeError("the 12 sheet tiles are identical; nothing to tell them apart")
    shapes = classify_frames(mp4, tiles, positions, w, h)
    if len(shapes) != len(times):
        n = min(len(shapes), len(times))
        shapes, times = shapes[:n], times[:n]
    duration = float(ref.get("duration") or max((p[1] for p in ref["phones"]), default=0.0))
    phones = normalize([Phone(float(s), float(e), str(lab)) for s, e, lab in ref["phones"]], duration)
    res = judge(shapes, times, fps, phones, set(plan["closed_shapes"]))
    return {
        "mp4": str(mp4), "fps": fps, "video_frames": len(shapes),
        "timing_source_of_clip": plan.get("timing_source", ""),
        "reference": f"independent alignment: {ref.get('source', 'unknown')}",
        "positions_compared": len(positions),
        **res,
    }


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def write_png_rgba(path: Path, w: int, h: int, rgba: bytes) -> None:
    """Write an 8-bit RGBA PNG with the standard library."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    rows = b"".join(b"\x00" + rgba[y * w * 4:(y + 1) * w * 4] for y in range(h))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def synthetic_sheet(path: Path, cell: int, n: int) -> None:
    """A sheet of n cells: a face color with a mouth rectangle of a different color and size per cell."""
    cells = []
    for k in range(n):
        px = bytearray()
        for y in range(cell):
            for x in range(cell):
                # A mouth block whose size and color depend on k; a transparent corner.
                if x < 2 and y < 2:
                    px += bytes((0, 0, 0, 0))
                elif 3 + (k % 4) * 2 <= x < 6 + (k % 4) * 2 + (k // 4) * 2 and 8 <= y < 8 + 1 + k:
                    px += bytes((250 - 17 * k, 40 + 15 * k, 60 + 5 * k, 255))
                else:
                    px += bytes((200, 180, 150, 255))
        cells.append(bytes(px))
    rows = b""
    for y in range(cell):
        rows += b"".join(c[y * cell * 4:(y + 1) * cell * 4] for c in cells)
    write_png_rgba(path, cell * n, cell, rows)


def selftest() -> None:
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        print("SKIP: end-to-end check needs ffmpeg and ffprobe")
        return
    import math
    import wave
    shapes = ["rest", "closed", "small_open", "medium_open", "wide_open", "smile",
              "round_small", "pucker", "teeth", "hiss", "tongue", "jaw_drop"]
    cell, scale, fps = 16, 4, 12
    ref_phones = [
        [0.0, 0.3, "sil"], [0.3, 0.4, "B"], [0.4, 0.8, "AA1"], [0.8, 0.9, "M"], [0.9, 1.0, "AA1"],
        [1.0, 1.5, "sil"], [1.5, 1.6, "P"], [1.6, 2.0, "AA1"],
    ]
    ref = {"text": "t", "duration": 2.0, "source": "selftest", "phones": ref_phones}
    n_frames = 24

    def frames_for(open_in_b: bool) -> list[str]:
        out = []
        for k in range(n_frames):
            s, e = k / fps, (k + 1) / fps
            bil = any(p[2] in ("B", "M", "P") and p[0] < e and p[1] > s for p in ref_phones)
            pause = any(p[2] == "sil" and p[0] <= s + 1e-6 and e <= p[1] + 1e-6 for p in ref_phones)
            out.append("closed" if bil else "rest" if pause else "wide_open")
        if open_in_b:
            for k in (3, 4):  # the frames on screen during /b/ (0.30 to 0.40 s)
                out[k] = "wide_open"
            out[14] = "wide_open"  # a frame inside the 1.0 to 1.5 s pause
        return out

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        sheet = tmp_dir / "sheet.png"
        synthetic_sheet(sheet, cell, 12)
        # The tiles as the video shows them: the sheet cells over the background, scaled by 4.
        bg = (0x1e, 0x1e, 0x2e)
        data = sheet.read_bytes()
        w_img = cell * 12
        idat = b""
        pos = 8
        while pos < len(data):
            ln = struct.unpack(">I", data[pos:pos + 4])[0]
            if data[pos + 4:pos + 8] == b"IDAT":
                idat += data[pos + 8:pos + 8 + ln]
            pos += 12 + ln
        raw = zlib.decompress(idat)
        stride = w_img * 4 + 1
        tiles = []
        for k in range(12):
            rows = []
            for y in range(cell):
                line = raw[y * stride + 1:(y + 1) * stride][k * cell * 4:(k + 1) * cell * 4]
                row = b""
                for x in range(cell):
                    r, g, b, a = line[x * 4:x * 4 + 4]
                    px = bytes((r, g, b)) if a else bytes(bg)
                    row += px * scale
                rows += [row] * scale
            tiles.append(b"".join(rows))

        wav = tmp_dir / "a.wav"
        with wave.open(str(wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b"".join(
                struct.pack("<h", 0 if 1.0 <= i / 16000 < 1.5 else int(8000 * math.sin(2 * math.pi * 220 * i / 16000)))
                for i in range(32000)))

        def render(frames: list[str], out: Path) -> None:
            cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                   "-s", f"{cell * scale}x{cell * scale}", "-r", str(fps), "-i", "-", "-i", str(wav),
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-shortest", str(out)]
            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            for name in frames:
                proc.stdin.write(tiles[shapes.index(name)])
            proc.stdin.close()
            assert proc.wait() == 0, "ffmpeg could not encode the test clip"

        def plan_for(frames: list[str]) -> dict:
            return {"fps": fps, "duration": 2.0, "shapes": shapes, "closed_shapes": ["closed", "rest"],
                    "frames": frames, "cell": cell, "background": "#1e1e2e", "timing_source": "selftest"}

        good = frames_for(False)
        bad = frames_for(True)
        mp4 = tmp_dir / "good.mp4"
        render(good, mp4)
        res = check(mp4, sheet, plan_for(good), ref)
        assert res["video_frames"] == n_frames, res["video_frames"]
        assert res["bilabials"] == 3 and res["long_pauses"] == 2, res
        assert res["pass"] and res["misses"] == 0, res
        mp4b = tmp_dir / "bad.mp4"
        render(bad, mp4b)
        res = check(mp4b, sheet, plan_for(bad), ref)
        assert not res["pass"] and res["misses"] == 2, res
        assert {m["kind"] for m in res["missed"]} == {"B", "pause"}, res["missed"]
    print("selftest OK: check_closures")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check 3: closed mouth on every /p b m/ and every long pause.")
    ap.add_argument("mp4", type=Path, nargs="?", help="the rendered clip")
    ap.add_argument("--sheet", type=Path, help="sprite sheet PNG (one cell per shape)")
    ap.add_argument("--plan", type=Path, help="plan file (shapes, closed_shapes, cell, background)")
    ap.add_argument("--phones", type=Path, help="reference phones file from an independent forced alignment")
    ap.add_argument("--out", type=Path, help="write the result JSON here")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    a = ap.parse_args(argv)
    if a.selftest:
        selftest()
        return 0
    if not (a.mp4 and a.sheet and a.plan and a.phones):
        ap.error("clip.mp4, --sheet, --plan and --phones are required")
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        print("error: ffmpeg and ffprobe must be on PATH", file=sys.stderr)
        return 2
    try:
        plan = json.loads(a.plan.read_text())
        ref = json.loads(a.phones.read_text())
        result = check(a.mp4, a.sheet, plan, ref)
    except (OSError, RuntimeError, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=1))
    print(f"CHECK 3 {'PASS' if result['pass'] else 'FAIL'}: {result['misses']} of {result['bilabials']} /p b m/ "
          f"and {result['long_pauses']} pauses over 150 ms miss a closed-mouth frame")
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(result, indent=1) + "\n")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
