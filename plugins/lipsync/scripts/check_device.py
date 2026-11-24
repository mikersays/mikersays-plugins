#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "numpy",
# ]
# ///
"""Check a simulator clip of a device pack: framebuffers, timing, closed mouths.

Needs `ffmpeg` and `ffprobe` on PATH, and numpy.

The check reads the finished MP4 from `device_sim.py`, not the plan as
drawn. ffmpeg decodes every video frame; one pixel is taken from the center
of each enlarged panel pixel, which gives the panel's framebuffer back at
1x. The reference images come from the pack's own bytes: the base image
with each mouth frame on it, as the panel shows it. Each framebuffer is
matched to the nearest reference.

Framebuffer match: no framebuffer may have a pixel that is 64 or more
levels from its reference (a 1-bit pixel on the wrong side of mid-gray, or a
wrong color). Pass: 0 such framebuffers.

Timing: every change of frame in the video is compared with the start of
the matching run in the pack. Pass: the video has exactly the pack's
changes, in order, and each one is within one panel frame (1/60 s at
60 fps) of its planned time.

Closed mouth (only with `--phones`): the reference phones come from an
INDEPENDENT forced alignment of the clip's sound (`align_mfa.py`), not from
the plan's own phones. Every /p b m/ must have a closed frame on screen
during the phoneme, and every pause over 150 ms must show only closed
frames, on at least one framebuffer. The closed frames are the bits of the
pack's closed mask. Pass: 0 misses. A clip made with `--speaker none` has no
sound; align the WAV that went into the pack instead.

Inputs: `clip.mp4`, with `clip.sim.json` next to it (it holds the scale and
the path of the pack; `--pack` names the pack when it has moved).

Exit code 0 when every check that ran passed, 1 when one failed. The last
lines are `DEVICE CHECK FRAMEBUFFER|TIMING|CLOSURES PASS|FAIL|SKIPPED`.

Usage:
    uv run check_device.py line.oled.mp4 [--phones reference.json] [--out result.json]
    uv run check_device.py --selftest
"""

from __future__ import annotations

import argparse
import json
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

HEADER_SIZE = 64
HEADER_FORMAT = "<4sBBBB2H4H4HIIIHHIIIII"
PIX_MONO_VPAGE, PIX_RGB565_BE = 1, 2

LONG_PAUSE = 0.150
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


def run(cmd: list[str]) -> bytes:
    proc = subprocess.run(cmd, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {proc.stderr.decode(errors='replace').strip()[-300:]}")
    return proc.stdout


# ---------------------------------------------------------------------------
# The pack: header, runs, and the images as the panel shows them
# ---------------------------------------------------------------------------

def read_pack(data: bytes) -> dict:
    """Parse a pack: the header fields, the runs, and the image bytes."""
    if len(data) < HEADER_SIZE or data[:4] != b"PNPK":
        raise RuntimeError("not a pack: no PNPK magic")
    f = struct.unpack_from(HEADER_FORMAT, data)
    k = {"pixel_format": f[2], "frame_count": f[4], "panel": (f[5], f[6]), "base": f[7:11], "mouth": f[11:15],
         "sample_rate": f[15], "sample_count": f[16], "run_count": f[17], "closed_mask": f[19]}
    if k["pixel_format"] not in (PIX_MONO_VPAGE, PIX_RGB565_BE):
        raise RuntimeError(f"unknown pixel format {k['pixel_format']}")
    base_off, frames_off, runs_off = f[20], f[21], f[22]
    size = image_bytes(k["pixel_format"], k["mouth"][2], k["mouth"][3])
    k["base_image"] = data[base_off:base_off + image_bytes(k["pixel_format"], k["base"][2], k["base"][3])]
    k["frames"] = [data[frames_off + i * size:frames_off + (i + 1) * size] for i in range(k["frame_count"])]
    # Runs as [start sample, frame index]; neighbors on one frame join (a
    # run field holds 24 bits, so the exporter splits a very long run).
    runs: list[list[int]] = []
    t = 0
    for i in range(k["run_count"]):
        frame = data[runs_off + i * 4]
        dur = int.from_bytes(data[runs_off + i * 4 + 1:runs_off + i * 4 + 4], "little")
        if not runs or runs[-1][1] != frame:
            runs.append([t, frame])
        t += dur
    k["runs"] = runs
    k["closed_frames"] = [i for i in range(k["frame_count"]) if k["closed_mask"] >> i & 1]
    return k


def image_bytes(pixel_format: int, w: int, h: int) -> int:
    return w * h // 8 if pixel_format == PIX_MONO_VPAGE else w * h * 2


def decode_image(pixel_format: int, w: int, h: int, blob: bytes):
    """Pack bytes -> an (h, w, 3) uint8 image, by the simulator's rule."""
    import numpy as np
    if pixel_format == PIX_MONO_VPAGE:
        pages = np.frombuffer(blob, np.uint8).reshape(h // 8, 1, w)
        bits = (pages >> np.arange(8, dtype=np.uint8).reshape(1, 8, 1)) & 1
        on = (bits.reshape(h, w) * 255).astype(np.uint8)
        return np.stack([on, on, on], -1)
    v = np.frombuffer(blob, ">u2").reshape(h, w).astype(np.uint16)
    r, g, b = v >> 11, (v >> 5) & 63, v & 31
    return np.stack([(r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)], -1).astype(np.uint8)


def reference_images(k: dict) -> list:
    """The full-panel image of each pack frame: the base with that mouth on it."""
    import numpy as np
    pw, ph = k["panel"]
    fmt = k["pixel_format"]
    panel = np.zeros((ph, pw, 3), np.uint8)
    bx, by, bw, bh = k["base"]
    panel[by:by + bh, bx:bx + bw] = decode_image(fmt, bw, bh, k["base_image"])
    mx, my, mw, mh = k["mouth"]
    out = []
    for blob in k["frames"]:
        img = panel.copy()
        img[my:my + mh, mx:mx + mw] = decode_image(fmt, mw, mh, blob)
        out.append(img)
    return out


# ---------------------------------------------------------------------------
# The video
# ---------------------------------------------------------------------------

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


def classify_video(mp4: Path, w: int, h: int, scale: int, refs: list) -> tuple[list[int], float, int]:
    """Name the nearest pack frame for each framebuffer of the video.

    Returns (frame indexes, largest mean absolute error of a match on the
    0-255 scale, count of framebuffers with a pixel 64 or more levels off).
    """
    import numpy as np
    ref = np.stack(refs).astype(np.int16)
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(mp4), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                            stdout=subprocess.PIPE)
    size = w * h * 3
    out: list[int] = []
    worst, inexact = 0.0, 0
    while True:
        buf = proc.stdout.read(size)
        while buf and len(buf) < size:
            more = proc.stdout.read(size - len(buf))
            if not more:
                break
            buf += more
        if len(buf) < size:
            break
        # One pixel from the center of each enlarged panel pixel.
        fb = np.frombuffer(buf, np.uint8).reshape(h, w, 3)[scale // 2::scale, scale // 2::scale].astype(np.int16)
        err = np.abs(ref - fb).reshape(len(refs), -1)
        i = int(err.mean(1).argmin())
        out.append(i)
        worst = max(worst, float(err[i].mean()))
        if int(err[i].max()) >= 64:
            inexact += 1
    proc.stdout.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg could not decode the video")
    return out, worst, inexact


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------

def check_timing(shown: list[int], times: list[float], runs: list[list[int]], rate: int, panel_fps: float) -> dict:
    """Compare the video's frame changes with the starts of the pack's runs."""
    plan = [(start / rate, frame) for start, frame in runs]
    seen = [(times[i], s) for i, s in enumerate(shown) if i == 0 or s != shown[i - 1]]
    limit = 1.0 / panel_fps
    same_order = [f for _, f in plan] == [f for _, f in seen]
    errors = [v - p for (p, _), (v, _) in zip(plan, seen)] if same_order else []
    worst = max((abs(e) for e in errors), default=None)
    return {
        "plan_changes": len(plan), "video_changes": len(seen), "same_frames_in_order": same_order,
        "limit_ms": round(limit * 1000, 3),
        "max_abs_error_ms": None if worst is None else round(worst * 1000, 3),
        "min_error_ms": round(min(errors) * 1000, 3) if errors else None,
        "max_error_ms": round(max(errors) * 1000, 3) if errors else None,
        "mean_error_ms": round(sum(errors) / len(errors) * 1000, 3) if errors else None,
        "pass": bool(same_order and worst is not None and worst <= limit + 1e-9),
    }


def check_closures(shown: list[int], times: list[float], fps: float, phones: list[Phone], closed: set) -> dict:
    """Apply the closed-mouth rule to the frame on screen in each framebuffer."""
    spans = [(t, times[i + 1] if i + 1 < len(times) else t + 1 / fps) for i, t in enumerate(times)]
    misses, n_bilabial, n_pause = [], 0, 0
    for p in phones:
        if is_silence(p.label):
            if p.dur <= LONG_PAUSE:
                continue
            n_pause += 1
            on = [i for i, (s, e) in enumerate(spans) if s >= p.start - 1e-6 and e <= p.end + 1e-6]
            ok = bool(on) and all(shown[i] in closed for i in on)
            kind = "pause"
        elif strip_stress(p.label) in BILABIALS:
            n_bilabial += 1
            on = [i for i, (s, e) in enumerate(spans) if s < p.end and e > p.start]
            ok = any(shown[i] in closed for i in on)
            kind = p.label
        else:
            continue  # includes "spn": speech of unknown shape, not a pause
        if not ok:
            misses.append({"kind": kind, "start": round(p.start, 3), "end": round(p.end, 3),
                           "frames": sorted({shown[i] for i in on})})
    return {"bilabials": n_bilabial, "long_pauses": n_pause, "misses": len(misses), "missed": misses,
            "pass": not misses}


def check(mp4: Path, pack_path: Path | None = None, ref: dict | None = None) -> dict:
    sim_path = Path(str(mp4.with_suffix("")) + ".sim.json")
    if not sim_path.exists():
        raise RuntimeError(f"no {sim_path}; the clip must come from device_sim.py")
    sim = json.loads(sim_path.read_text())
    pack_path = pack_path or Path(sim.get("pack_file", ""))
    if not pack_path.is_file():
        raise RuntimeError(f"cannot find the pack {str(pack_path)!r}; give --pack")
    k = read_pack(pack_path.read_bytes())
    scale = int(sim["scale"])
    w, h, fps, times = probe_video(mp4)
    pw, ph = k["panel"]
    if (w, h) != (pw * scale, ph * scale):
        raise RuntimeError(f"the video is {w}x{h}; a {pw}x{ph} panel at scale {scale} is {pw * scale}x{ph * scale}")
    shown, worst, inexact = classify_video(mp4, w, h, scale, reference_images(k))
    n = min(len(shown), len(times))
    shown, times = shown[:n], times[:n]
    info = sim.get("pack") or {}
    result = {
        "mp4": str(mp4), "pack": str(pack_path), "target": info.get("target"), "speaker": sim.get("speaker"),
        "panel": [pw, ph], "panel_fps": fps, "video_frames": n,
        "frames": info.get("frames"), "closed_frames": k["closed_frames"],
        "framebuffer_match": {"largest_mean_abs_error": round(worst, 3), "inexact_framebuffers": inexact,
                              "pass": inexact == 0},
        "timing": check_timing(shown, times, k["runs"], k["sample_rate"], fps),
    }
    if ref is None:
        result["closures"] = {"skipped": "no --phones reference"}
    else:
        duration = k["sample_count"] / k["sample_rate"]
        phones = normalize([Phone(float(s), float(e), str(lab)) for s, e, lab in ref["phones"]], duration)
        result["closures"] = check_closures(shown, times, fps, phones, set(k["closed_frames"]))
        result["closures"]["reference"] = f"independent alignment: {ref.get('source', 'unknown')}"
    result["pass"] = bool(result["framebuffer_match"]["pass"] and result["timing"]["pass"]
                          and result["closures"].get("pass", True))
    return result


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def _tiny_pack(pixel_format: int) -> bytes:
    """A 16x16 pack: 3 mouth frames at (8, 8) 8x8, 5 runs, 0.5 s at 8000 Hz, no audio."""
    if pixel_format == PIX_MONO_VPAGE:
        base = bytes([0xFF] * 32)
        frames = [bytes([v] * 8) for v in (0xFF, 0x0F, 0x00)]
    else:
        base = bytes([0xFF, 0xE0] * 256)
        frames = [bytes(pair * 64) for pair in ([0xFF, 0xE0], [0x00, 0x1F], [0xF8, 0x00])]
    runs = [(0, 800), (1, 1200), (2, 400), (1, 800), (0, 800)]
    run_bytes = b"".join(bytes([i]) + d.to_bytes(3, "little") for i, d in runs)
    frames_off = HEADER_SIZE + len(base)
    runs_off = frames_off + sum(len(f) for f in frames)
    header = struct.pack(HEADER_FORMAT, b"PNPK", 1, pixel_format, 0, 3, 16, 16, 0, 0, 16, 16, 8, 8, 8, 8,
                         8000, 4000, len(runs), 0, 0b001, HEADER_SIZE, frames_off, runs_off,
                         runs_off + len(run_bytes), 0)
    return header + base + b"".join(frames) + run_bytes


def selftest() -> None:
    # Timing rule, on frame lists (no video needed).
    runs = [[0, 0], [800, 1], [2000, 2]]
    times = [i / 60 for i in range(30)]
    shown = [0] * 6 + [1] * 9 + [2] * 15
    t = check_timing(shown, times, runs, 8000, 60)
    assert t["pass"] and t["video_changes"] == 3 and t["max_abs_error_ms"] == 0.0, t
    late = [0] * 8 + [1] * 7 + [2] * 15    # the first change is 2 panel frames late
    t = check_timing(late, times, runs, 8000, 60)
    assert not t["pass"] and abs(t["max_abs_error_ms"] - 33.333) < 0.01, t
    t = check_timing([0] * 6 + [2] * 24, times, runs, 8000, 60)   # a change is missing
    assert not t["pass"] and not t["same_frames_in_order"], t

    # Closed-mouth rule: frame 0 is closed. M at 0.20 to 0.25 s has frame 1 on
    # screen (a miss); the pause 0.25 to 0.50 s shows frame 2 (a miss).
    phones = normalize([Phone(0.0, 0.1, "sil"), Phone(0.1, 0.2, "AA1"), Phone(0.2, 0.25, "M")], 0.5)
    c = check_closures(shown, times, 60, phones, {0})
    assert c["bilabials"] == 1 and c["long_pauses"] == 1 and c["misses"] == 2, c
    good = [0] * 6 + [1] * 6 + [0] * 18
    c = check_closures(good, times, 60, phones, {0})
    assert c["pass"] and c["misses"] == 0, c

    try:
        import numpy as np
    except ImportError:
        print("selftest OK: check_device (timing and closure rules; video tests skipped: numpy is missing)")
        return

    # Pack decoding: the 1-bit page byte 0x0F lights the top 4 rows of a column.
    k = read_pack(_tiny_pack(PIX_MONO_VPAGE))
    assert k["runs"] == [[0, 0], [800, 1], [2000, 2], [2400, 1], [3200, 0]] and k["closed_frames"] == [0], k["runs"]
    refs = reference_images(k)
    assert refs[1][8:12, 8:16].min() == 255 and refs[1][12:16, 8:16].max() == 0 and refs[1][:8].min() == 255
    c = read_pack(_tiny_pack(PIX_RGB565_BE))
    crefs = reference_images(c)
    assert tuple(crefs[0][0, 0]) == (255, 255, 0) and tuple(crefs[1][9, 9]) == (0, 0, 255), crefs[1][9, 9]

    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        print("selftest OK: check_device (rules and pack decoding; video tests skipped: ffmpeg is missing)")
        return
    # Round trip: draw the pack's plan as a 60 fps video at scale 4, then
    # read it back. One clip is on time; one shows every frame 3 panel frames late.
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        for fmt, pack_refs, pk in ((PIX_MONO_VPAGE, refs, k), (PIX_RGB565_BE, crefs, c)):
            pack = tmp / f"tiny{fmt}.pnpk"
            pack.write_bytes(_tiny_pack(fmt))
            for name, delay, expect in (("ontime", 0, True), ("late", 3, False)):
                raw = bytearray()
                for n in range(30):
                    sample = max(0, n - delay) * 8000 // 60
                    frame = [f for s, f in pk["runs"] if s <= sample][-1]
                    raw += np.repeat(np.repeat(pack_refs[frame], 4, 0), 4, 1).tobytes()
                mp4 = tmp / f"{name}{fmt}.mp4"
                proc = subprocess.run(
                    ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "64x64",
                     "-r", "60", "-i", "-", "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p", str(mp4)],
                    input=bytes(raw), capture_output=True)
                assert proc.returncode == 0, proc.stderr
                Path(str(mp4.with_suffix("")) + ".sim.json").write_text(json.dumps(
                    {"pack": {}, "pack_file": str(pack), "scale": 4, "speaker": "none", "panel_fps": 60}))
                res = check(mp4)
                assert res["framebuffer_match"]["pass"], res["framebuffer_match"]
                assert res["timing"]["pass"] is expect and res["pass"] is expect, (name, fmt, res["timing"])
                assert res["timing"]["video_changes"] == 5, res["timing"]
    print("selftest OK: check_device")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check a simulator clip of a device pack.")
    ap.add_argument("mp4", type=Path, nargs="?", help="clip from device_sim.py (its .sim.json lies next to it)")
    ap.add_argument("--pack", type=Path, help="the pack, when it is not where the .sim.json says")
    ap.add_argument("--phones", type=Path, help="reference phones file from an independent forced alignment")
    ap.add_argument("--out", type=Path, help="write the result JSON here")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    a = ap.parse_args(argv)
    if a.selftest:
        selftest()
        return 0
    if not a.mp4:
        ap.error("a clip is required")
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        print("error: ffmpeg and ffprobe must be on PATH", file=sys.stderr)
        return 2
    try:
        import numpy  # noqa: F401
    except ImportError:
        print("error: numpy is missing; run this script with `uv run`", file=sys.stderr)
        return 2
    try:
        ref = json.loads(a.phones.read_text()) if a.phones else None
        result = check(a.mp4, a.pack, ref)
    except (OSError, RuntimeError, KeyError, ValueError, struct.error, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1))
    m, t, c = result["framebuffer_match"], result["timing"], result["closures"]
    print(f"DEVICE CHECK FRAMEBUFFER {'PASS' if m['pass'] else 'FAIL'}: {m['inexact_framebuffers']} of "
          f"{result['video_frames']} framebuffers differ from their pack frame")
    print(f"DEVICE CHECK TIMING {'PASS' if t['pass'] else 'FAIL'}: {t['video_changes']} changes for "
          f"{t['plan_changes']} planned, largest error {t['max_abs_error_ms']} ms, limit {t['limit_ms']} ms")
    if "skipped" in c:
        print(f"DEVICE CHECK CLOSURES SKIPPED: {c['skipped']}")
    else:
        print(f"DEVICE CHECK CLOSURES {'PASS' if c['pass'] else 'FAIL'}: {c['misses']} of {c['bilabials']} /p b m/ "
              f"and {c['long_pauses']} pauses over 150 ms miss a closed-mouth frame")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
