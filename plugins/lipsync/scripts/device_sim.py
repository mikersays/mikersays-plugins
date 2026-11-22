#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Play a device pack in the pixel-exact simulator and write an MP4.

Stdlib only. Needs `cc` (any C99 compiler) and `ffmpeg` on PATH.

The simulator (`pn_sim.c`) is the firmware's player code (`pn_player.c`),
compiled for this computer, with an imitation speaker and panel. This
wrapper compiles it when the binary is missing or older than its sources,
runs it on the pack, and hands the recorded panel frames and speaker output
to ffmpeg. The C sources ship with the plugin, in
`skills/lipsync-device/assets/device/` (`--src DIR` names another copy).

Input: a pack from `device_pack.py`. When `<pack>.json` lies next to it, the
wrapper copies it into the output and takes `panel_fps` from it.

Output, for `--out clip.mp4`:
  clip.mp4         the panel's own pixel grid, enlarged by a whole number
                   (`--scale`) with nearest neighbor, at the panel frame
                   rate, with the sound that the speaker played
  clip.events.csv  every draw and its time: `time_us,event,frame`
  clip.sim.json    the pack's description, the path of the pack, and the
                   simulator's settings; `check_device.py` reads it

The simulator's speaker is ideal: it plays at exactly the sample rate and
has no codec delay and no jitter. The clip proves the player's logic and the
pack. It does not prove the real audio latency of a board.

Usage:
    uv run device_sim.py line.oled.pnpk --out line.oled.mp4
    uv run device_sim.py line.oled.pnpk --out silent.mp4 --speaker none
    uv run device_sim.py --selftest

Options: `--scale N` (default 4 for a 1-bit pack, 2 for RGB565),
`--speaker m5|i2s|none` (default i2s for a 1-bit pack, m5 for RGB565; `none`
makes the player follow the timer), `--loop-us N` (time of one firmware loop
pass, default 2000), `--draw-us N` (time one mouth frame takes to reach the
glass; default 3300 for 1 bit over I2C, 700 for RGB565), `--lead-us N` (the
HAL's `draw_lead_us`; default 2 x loop-us + draw-us), `--build-dir DIR`
(where the binary goes; default: a folder in the system's temporary files).
Exit code 0 on success; non-zero with a one-line reason on failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HEADER_SIZE = 64
HEADER_FORMAT = "<4sBBBB2H4H4HIIIHHIIIII"
PIX_MONO_VPAGE, PIX_RGB565_BE = 1, 2
SOURCES = ("sim/pn_sim.c", "lib/pnplayer/pn_player.c", "lib/pnplayer/pn_player.h")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{Path(cmd[0]).name} failed: {proc.stderr.strip()[-300:]}")
    return proc


def default_src() -> Path:
    """Return the bundled `device/` folder: the plugin's `skills/lipsync-device/assets/device`."""
    return Path(__file__).resolve().parent.parent / "skills" / "lipsync-device" / "assets" / "device"


def build_sim(src: Path, build_dir: Path | None = None) -> Path:
    """Compile the simulator when it is missing or stale. Return its path."""
    files = [src / rel for rel in SOURCES]
    for f in files:
        if not f.exists():
            raise RuntimeError(f"no {f}; give --src the folder that holds sim/ and lib/pnplayer/")
    if build_dir is None:
        # One folder per copy of the sources, so two copies never share a binary.
        tag = hashlib.sha256(str(src.resolve()).encode()).hexdigest()[:12]
        build_dir = Path(tempfile.gettempdir()) / f"lipsync-pn-sim-{tag}"
    binary = build_dir / "pn_sim"
    if binary.exists() and all(binary.stat().st_mtime >= f.stat().st_mtime for f in files):
        return binary
    if not shutil.which("cc"):
        raise RuntimeError("cc must be on PATH to compile the simulator")
    build_dir.mkdir(parents=True, exist_ok=True)
    run(["cc", "-std=c99", "-O2", "-Wall", "-Wextra", "-I", str(files[2].parent),
         "-o", str(binary), str(files[0]), str(files[1])])
    return binary


def read_header(data: bytes) -> dict:
    """Parse the fields of the 64-byte pack header that the wrapper needs."""
    if len(data) < HEADER_SIZE or data[:4] != b"PNPK":
        raise RuntimeError("not a pack: no PNPK magic")
    f = struct.unpack_from(HEADER_FORMAT, data)
    return {"pixel_format": f[2], "panel": [f[5], f[6]], "sample_rate": f[15], "sample_count": f[16]}


def simulate(pack: Path, out: Path, src: Path, scale: int | None = None, speaker: str | None = None,
             extra: list[str] | None = None, build_dir: Path | None = None) -> dict:
    """Run the simulator on `pack` and write `out` (MP4). Return the settings."""
    head = read_header(pack.read_bytes())
    info_path = Path(str(pack) + ".json")
    info = json.loads(info_path.read_text()) if info_path.exists() else {}
    w, h = head["panel"]
    mono = head["pixel_format"] == PIX_MONO_VPAGE
    fps = int(info.get("panel_fps", 60))
    scale = scale or (4 if mono else 2)
    speaker = speaker or ("i2s" if mono else "m5")
    if (w * scale) % 2 or (h * scale) % 2:
        raise RuntimeError(f"video size {w * scale}x{h * scale} is odd; H.264 needs an even size (change --scale)")
    binary = build_sim(src, build_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    stem = out.with_suffix("")
    events = Path(str(stem) + ".events.csv")
    with tempfile.TemporaryDirectory(prefix="pn-sim-") as tmp:
        rgb, pcm = Path(tmp) / "frames.rgb", Path(tmp) / "audio.s16"
        sim = run([str(binary), str(pack), str(rgb), str(pcm), str(events),
                   "--speaker", speaker, "--panel-fps", str(fps)] + (extra or []))
        run(["ffmpeg", "-y", "-loglevel", "error",
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", str(rgb),
             "-f", "s16le", "-ar", str(head["sample_rate"]), "-ac", "1", "-i", str(pcm),
             "-vf", f"scale={w * scale}:{h * scale}:flags=neighbor",
             "-c:v", "libx264", "-preset", "slow", "-crf", "10", "-tune", "animation",
             "-pix_fmt", "yuv420p", "-r", str(fps),
             "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)])
    doc = {"pack": info, "pack_file": str(pack.resolve()), "panel": [w, h], "scale": scale, "speaker": speaker,
           "panel_fps": fps, "simulator": sim.stderr.strip(), "options": extra or []}
    Path(str(stem) + ".sim.json").write_text(json.dumps(doc) + "\n")
    return doc


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def _tiny_pack() -> bytes:
    """A 16x16 1-bit pack: 3 frames, 5 runs, 0.5 s of PCM16 at 8000 Hz."""
    base = bytes([0xFF] * 32)
    frames = [bytes([v] * 8) for v in (0xFF, 0x0F, 0x00)]
    runs = [(0, 800), (1, 1200), (2, 400), (1, 800), (0, 800)]
    n = sum(d for _, d in runs)
    audio = struct.pack(f"<{n}h", *[(i * 37) % 2000 - 1000 for i in range(n)])
    run_bytes = b"".join(bytes([i]) + d.to_bytes(3, "little") for i, d in runs)
    frames_off = HEADER_SIZE + len(base)
    runs_off = frames_off + 24
    audio_off = runs_off + len(run_bytes)
    header = struct.pack(HEADER_FORMAT, b"PNPK", 1, PIX_MONO_VPAGE, 1, 3, 16, 16, 0, 0, 16, 16, 8, 8, 8, 8,
                         8000, n, len(runs), 0, 0b001, HEADER_SIZE, frames_off, runs_off, audio_off, len(audio))
    return header + base + b"".join(frames) + run_bytes + audio


def selftest() -> None:
    head = read_header(_tiny_pack())
    assert head == {"pixel_format": 1, "panel": [16, 16], "sample_rate": 8000, "sample_count": 4000}, head
    src = default_src()
    if not all((src / rel).exists() for rel in SOURCES):
        print(f"SKIP: the simulator sources are not in {src}")
        return
    if not (shutil.which("cc") and shutil.which("ffmpeg") and shutil.which("ffprobe")):
        print("SKIP: the simulator needs cc, ffmpeg and ffprobe")
        return
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        pack = tmp / "tiny.pnpk"
        pack.write_bytes(_tiny_pack())
        for speaker in ("i2s", "none"):
            out = tmp / f"{speaker}.mp4"
            doc = simulate(pack, out, src, speaker=speaker, build_dir=tmp / "build")
            assert doc["scale"] == 4 and doc["panel"] == [16, 16] and "5 frame changes" in doc["simulator"], doc
            rows = Path(str(out.with_suffix("")) + ".events.csv").read_text().split()
            assert rows[0] == "time_us,event,frame" and rows[1].endswith(",base,-1"), rows[:2]
            assert [r.split(",")[2] for r in rows[2:]] == ["0", "1", "2", "1", "0"], rows
            # Each frame reaches the glass within one panel frame of its run's start.
            for row, start in zip(rows[2:], (0, 800, 2000, 2400, 3200)):
                assert abs(int(row.split(",")[0]) - start * 1000000 // 8000) <= 16667, (speaker, row, start)
            probe = json.loads(run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                                    "-show_entries", "stream=width,height,nb_read_frames", "-of", "json",
                                    str(out)]).stdout)["streams"][0]
            assert (probe["width"], probe["height"], int(probe["nb_read_frames"])) == (64, 64, 30), probe
            assert json.loads(Path(str(out.with_suffix("")) + ".sim.json").read_text())["speaker"] == speaker
    print("selftest OK: device_sim")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Play a device pack in the simulator and write an MP4.")
    ap.add_argument("pack", type=Path, nargs="?", help="pack from device_pack.py")
    ap.add_argument("--out", type=Path, help="MP4 to write")
    ap.add_argument("--scale", type=int, help="whole-number enlargement (default: 4 for 1 bit, 2 for RGB565)")
    ap.add_argument("--speaker", choices=["m5", "i2s", "none"],
                    help="audio output to imitate (default: i2s for 1 bit, m5 for RGB565)")
    ap.add_argument("--loop-us", type=int, help="time of one firmware loop pass in microseconds (default 2000)")
    ap.add_argument("--draw-us", type=int, help="time one mouth frame takes to reach the glass")
    ap.add_argument("--lead-us", type=int, help="the HAL's draw_lead_us (default: 2 x loop-us + draw-us)")
    ap.add_argument("--src", type=Path, help="folder with sim/pn_sim.c and lib/pnplayer/ (default: the bundled copy)")
    ap.add_argument("--build-dir", type=Path, help="where to put the simulator binary")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    a = ap.parse_args(argv)
    if a.selftest:
        selftest()
        return 0
    if not (a.pack and a.out):
        ap.error("a pack and --out are required")
    if not shutil.which("ffmpeg"):
        print("error: ffmpeg must be on PATH", file=sys.stderr)
        return 2
    extra: list[str] = []
    for flag, value in (("--loop-us", a.loop_us), ("--draw-us", a.draw_us), ("--lead-us", a.lead_us)):
        if value is not None:
            extra += [flag, str(value)]
    try:
        out = a.out.with_suffix(".mp4")
        doc = simulate(a.pack, out, a.src or default_src(), a.scale, a.speaker, extra, a.build_dir)
    except (OSError, RuntimeError, ValueError, struct.error, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"{out}  {doc['simulator']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
