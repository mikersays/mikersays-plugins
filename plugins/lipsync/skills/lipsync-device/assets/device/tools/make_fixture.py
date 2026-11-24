#!/usr/bin/env python3
"""Write test/test_player/fixture.h: two tiny packs for the unit tests.

    python3 tools/make_fixture.py [--exporter PATH/device_pack.py] [--check]

Stdlib only. The packs come from the same Python code that exports real
packs (`device_pack.py` of the lipsync plugin), so the tests also prove that
the exporter and the C player agree on the byte layout and on the ADPCM
decoder. Run this again when the pack format changes.

`--exporter` names `device_pack.py`. The default is the plugin's
`scripts/device_pack.py`, found from this file's place inside the plugin; a
copy of this project outside the plugin needs the option. `--check` writes
nothing and exits with 1 when fixture.h differs from what would be written.

MONO pack:  16x16 panel, 1 bit per pixel, mouth at (8, 8) 8x8, 3 frames,
            5 runs, 1200 samples of a rising tone at 8000 Hz as IMA ADPCM.
            FIXTURE_PCM holds the samples that Python's decoder gives.
COLOR pack: 6x4 panel, RGB565, mouth at (2, 1) 3x2, 2 frames, 2 runs,
            40 samples of PCM16.
"""
import argparse
import importlib.util
import math
import sys
from pathlib import Path

DEVICE = Path(__file__).resolve().parent.parent
OUT = DEVICE / "test" / "test_player" / "fixture.h"
MONO_RUNS = [[0, 200], [1, 333], [2, 67], [1, 400], [0, 200]]
COLOR_RUNS = [[1, 25], [0, 15]]


def load_exporter(path: Path):
    if not path.exists():
        sys.exit(f"no exporter at {path}; give --exporter PATH/device_pack.py")
    spec = importlib.util.spec_from_file_location("device_pack", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["device_pack"] = mod
    spec.loader.exec_module(mod)
    return mod


def c_array(name: str, ctype: str, values, per_line: int) -> str:
    rows = [", ".join(str(int(v)) for v in values[i:i + per_line]) for i in range(0, len(values), per_line)]
    return f"static const {ctype} {name}[] = {{\n    " + ",\n    ".join(rows) + "\n};\n"


def fixture_text(pack) -> tuple[str, str]:
    """Return (the text of fixture.h, a one-line summary)."""
    n = 1200
    pcm = []
    for i in range(n):
        t = i / 8000
        pcm.append(int(12000 * math.sin(2 * math.pi * (200 + 900 * t) * t) * min(1, t * 40)))
    base = bytes(range(1, 33))                                   # 16 columns x 2 pages
    frames = [bytes([i * 16 + c for c in range(8)]) for i in (1, 2, 3)]
    mono, _ = pack.assemble_pack(pack.PIX_MONO_VPAGE, (16, 16), (8, 8, 8, 8), base, frames, MONO_RUNS, 0b001, 8000, pcm)
    decoded = pack.adpcm_decode(mono[-len(pack.adpcm_encode(pcm)):], n)

    cpcm = [i * 700 - 14000 for i in range(40)]
    cbase = bytes(range(100, 148))                               # 6 x 4 pixels x 2 bytes
    cframes = [bytes(range(10, 22)), bytes(range(30, 42))]       # 3 x 2 pixels x 2 bytes
    color, _ = pack.assemble_pack(pack.PIX_RGB565_BE, (6, 4), (2, 1, 3, 2), cbase, cframes, COLOR_RUNS, 0b10, 8000,
                                  cpcm, "pcm16")
    text = "/* Made by device/tools/make_fixture.py. Do not edit. */\n"
    text += c_array("FIXTURE_MONO", "uint8_t", mono, 20)
    text += c_array("FIXTURE_PCM", "int16_t", decoded, 12)
    text += c_array("FIXTURE_COLOR", "uint8_t", color, 20)
    text += c_array("FIXTURE_COLOR_PCM", "int16_t", cpcm, 12)
    err = [abs(a - b) for a, b in zip(decoded, pcm)]
    return text, (f"mono {len(mono)} bytes, color {len(color)} bytes, "
                  f"ADPCM error max {max(err)}, mean {sum(err) / len(err):.1f}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Write the unit tests' fixture packs.")
    ap.add_argument("--exporter", type=Path, default=Path(__file__).resolve().parents[5] / "scripts" / "device_pack.py",
                    help="path of device_pack.py (default: the plugin's scripts folder)")
    ap.add_argument("--check", action="store_true", help="compare with fixture.h instead of writing it")
    a = ap.parse_args()
    text, summary = fixture_text(load_exporter(a.exporter))
    if a.check:
        same = OUT.exists() and OUT.read_text() == text
        print(f"{OUT}: {'matches the exporter' if same else 'DIFFERS from the exporter'} ({summary})")
        sys.exit(0 if same else 1)
    OUT.write_text(text)
    print(f"{OUT}: {summary}")


if __name__ == "__main__":
    main()
