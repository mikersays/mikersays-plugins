#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#     "mlx-audio==0.6.7",
#     "misaki[en]==0.9.4",
#     "num2words",
#     "phonemizer-fork",
#     "espeakng-loader",
#     "spacy==3.8.18",
#     "en-core-web-sm @ https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl",
#     "soundfile",
#     "numpy",
# ]
# ///
"""Run ONE text-to-speech model on a script and record timing and memory.

A generic single-model measurement run for mlx-audio models (Apple Silicon).
Inputs: `--repo` (a Hugging Face repo that mlx-audio can load, for example
`mlx-community/Kokoro-82M-bf16`) and `--text-file` (the script to speak).
Outputs: `--out sample.wav` (the audio) and `--json result.json` (the
measurements, also printed): load seconds, synthesis seconds, audio seconds,
real-time factor (RTF = synthesis seconds / audio seconds; below 1 is faster
than real time), and `mx.get_peak_memory()` in GB.

The synthesis time starts after a warm-up sentence, so the first-call cost
(kernel compilation) is not in it. `--max-chars N` packs whole sentences into
chunks of at most N characters, one `generate` call per chunk (models with a
short context need this); without it the whole script goes in one call.
`--prefix` is added to every chunk (for example `"[S1] "` for Dia), `--voice`
is passed to the model as `voice=...`, and every `--gen key=value` goes to
`model.generate` (the value is read as JSON when it parses, else as text).

Memory rules. Run ONE model at a time, strictly one after another, each in its
own process. Before loading, this script reads `memory_pressure` and
`sysctl vm.swapusage` (macOS) and refuses to start when free memory is under
30%, unless you pass `--force`. `mx.get_peak_memory()` counts only MLX
buffers, so the result also holds `max_rss_gb` (this process's peak resident
set size, from `resource.getrusage`). For the peak memory footprint that the
macOS Activity Monitor shows, wrap the run in `/usr/bin/time -l` and read
"peak memory footprint" from its report. Wrap the Python interpreter that has
the dependencies, not `uv run` itself: `time -l` would then measure uv, whose
child process holds the model.

    /usr/bin/time -l python3 tts_bakeoff.py --repo mlx-community/Kokoro-82M-bf16 \\
        --voice af_heart --text-file script.txt --out sample.wav --json result.json

    uv run tts_bakeoff.py --repo ... --text-file ... --out ... --json ...   # no footprint
    uv run tts_bakeoff.py --selftest        # sentence chunking and RTF arithmetic only
Exit code 0 on success; non-zero with a one-line reason on failure.
"""

from __future__ import annotations

import argparse
import json
import re
import resource
import subprocess
import sys
import time
from pathlib import Path

MIN_FREE_PCT = 30  # refuse to start below this share of free memory


def split_sentences(text: str, max_chars: int) -> list[str]:
    """Greedy-pack whole sentences into chunks of at most max_chars."""
    sents = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    cur = ""
    for s in sents:
        if cur and len(cur) + 1 + len(s) > max_chars:
            chunks.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        chunks.append(cur)
    return chunks


def rtf(synth_seconds: float, audio_seconds: float) -> float:
    """Real-time factor: seconds of synthesis per second of audio."""
    if audio_seconds <= 0:
        raise ValueError("no audio was produced")
    return synth_seconds / audio_seconds


def parse_gen(items: list[str]) -> dict:
    """Read `key=value` pairs; a value that parses as JSON becomes a number, bool or list."""
    out: dict = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep or not key:
            raise ValueError(f"bad --gen {item!r}; use key=value")
        try:
            out[key] = json.loads(value)
        except json.JSONDecodeError:
            out[key] = value
    return out


def free_memory_pct(report: str) -> int | None:
    """Read the free percentage from the last line of `memory_pressure` output."""
    m = re.search(r"free percentage:\s*(\d+)%", report)
    return int(m.group(1)) if m else None


def memory_gate(force: bool) -> None:
    """Print the memory state and refuse to start when free memory is under MIN_FREE_PCT."""
    try:
        mp = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=30).stdout
        swap = subprocess.run(["sysctl", "vm.swapusage"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return  # not macOS: nothing to read
    print(mp.strip().splitlines()[-1] if mp.strip() else "memory_pressure: no output")
    print(swap.strip())
    free = free_memory_pct(mp)
    if free is not None and free < MIN_FREE_PCT and not force:
        raise RuntimeError(f"free memory is {free}% (< {MIN_FREE_PCT}%); wait, or pass --force")


def run_generic(model, gen: dict, texts: list[str]):
    """Call model.generate per text; return (audio parts, sample rate)."""
    import numpy as np

    parts, sr = [], None
    for t in texts:
        for r in model.generate(text=t, **gen):
            parts.append(np.asarray(r.audio, dtype=np.float32).reshape(-1))
            sr = r.sample_rate
    return parts, sr


def measure(a: argparse.Namespace) -> dict:
    import mlx.core as mx
    import numpy as np
    import soundfile as sf
    from mlx_audio.tts.utils import load_model

    text = " ".join(a.text_file.read_text().split())
    if not text:
        raise ValueError("the script is empty")
    gen = parse_gen(a.gen or [])
    if a.voice:
        gen["voice"] = a.voice
    memory_gate(a.force)

    t0 = time.perf_counter()
    model = load_model(a.repo)
    load_s = time.perf_counter() - t0

    mx.random.seed(0)
    np.random.seed(0)
    chunks = split_sentences(text, a.max_chars) if a.max_chars else [text]
    texts = [a.prefix + c for c in chunks]

    run_generic(model, gen, [a.prefix + "Warm up."])  # excluded from timing
    mx.clear_cache()

    mx.random.seed(0)
    t0 = time.perf_counter()
    parts, sr = run_generic(model, gen, texts)
    mx.synchronize()
    synth_s = time.perf_counter() - t0
    if not parts:
        raise RuntimeError("the model returned no audio")

    audio = np.concatenate(parts)
    dur = len(audio) / sr
    a.out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(a.out, np.clip(audio, -1, 1), sr, subtype="PCM_16")
    return {
        "repo": a.repo, "runtime": "mlx-audio 0.6.7 (MLX)", "voice": a.voice or "model default",
        "chunks": len(chunks), "max_chars": a.max_chars, "prefix": a.prefix, "sample_rate": sr,
        "audio_seconds": round(dur, 2), "load_seconds": round(load_s, 2),
        "synth_seconds": round(synth_s, 2), "rtf": round(rtf(synth_s, dur), 3),
        "peak_mx_gb": round(mx.get_peak_memory() / 1e9, 2),
        "max_rss_gb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9, 2),  # bytes on macOS
        "segments_returned": len(parts), "gen_kwargs": gen,
    }


def selftest() -> None:
    text = "One. Two is longer. Three! Four? Five five five five."
    assert split_sentences(text, 1000) == [text]
    chunks = split_sentences(text, 20)
    assert chunks == ["One. Two is longer.", "Three! Four?", "Five five five five."], chunks
    assert all(len(c) <= 20 for c in chunks) and " ".join(chunks) == text
    assert split_sentences("A single very long sentence without a stop", 10) == ["A single very long sentence without a stop"]
    assert split_sentences("", 10) == []
    assert rtf(5.0, 20.0) == 0.25 and abs(rtf(12.3, 4.1) - 3.0) < 1e-9
    try:
        rtf(1.0, 0.0)
        raise AssertionError("expected ValueError for zero audio")
    except ValueError:
        pass
    assert parse_gen(["max_tokens=1200", "temperature=0.8", "flag=true", "voice=en-Emma_woman"]) == \
        {"max_tokens": 1200, "temperature": 0.8, "flag": True, "voice": "en-Emma_woman"}
    try:
        parse_gen(["novalue"])
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    assert free_memory_pct("...\nSystem-wide memory free percentage: 87%\n") == 87
    assert free_memory_pct("no number here") is None
    print("selftest OK: tts_bakeoff")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run one TTS model on a script and record timing and memory.")
    ap.add_argument("--repo", help="Hugging Face repo of the model, e.g. mlx-community/Kokoro-82M-bf16")
    ap.add_argument("--text-file", type=Path, help="the script to speak")
    ap.add_argument("--out", type=Path, help="WAV to write")
    ap.add_argument("--json", type=Path, help="result file to write")
    ap.add_argument("--voice", help="voice name, passed to the model as voice=...")
    ap.add_argument("--max-chars", type=int, help="pack whole sentences into chunks of at most N characters")
    ap.add_argument("--prefix", default="", help='text added before every chunk, e.g. "[S1] "')
    ap.add_argument("--gen", action="append", metavar="KEY=VALUE", help="extra model.generate argument (repeatable)")
    ap.add_argument("--force", action="store_true", help=f"start even when free memory is under {MIN_FREE_PCT}%%")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    a = ap.parse_args(argv)
    if a.selftest:
        selftest()
        return 0
    if not (a.repo and a.text_file and a.out and a.json):
        ap.error("--repo, --text-file, --out and --json are required")
    try:
        res = measure(a)
    except ImportError as e:
        print(f"error: missing package {e.name}; run this script with `uv run`", file=sys.stderr)
        return 1
    except (OSError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    a.json.parent.mkdir(parents=True, exist_ok=True)
    a.json.write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
