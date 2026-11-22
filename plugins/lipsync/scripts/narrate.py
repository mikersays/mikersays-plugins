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
"""Speech synthesis with phoneme timestamps (Kokoro-82M on Apple Silicon).

Inputs: the text (`--text "..."` or `--text-file f.txt`), `--voice` (default
`af_heart`) and `--speed`. Outputs: `--out narration.wav` (mono, 16-bit PCM)
and `--phones-out phones.json`, a phones file:
`{"text", "duration", "source", "voice", "phones": [[start, end, label], ...]}`
with ARPAbet labels (stress digit on vowels) and `sil` for silence.

Kokoro-82M exposes timing: its duration predictor returns `pred_dur`, one
duration per input symbol (each phoneme character, stress mark, space, and
punctuation mark, plus one start and one end symbol). The durations are in
frames of 600 samples at 24 kHz (25 ms). The decoder makes exactly that many
frames of audio, so the timestamps describe the audio that was synthesized;
they are not a guess from the text. A constant offset (KOKORO_OFFSET) lines
the duration grid up with the sound.

Needs an Apple Silicon Mac (MLX). The first run downloads the model (about
330 MB) from Hugging Face; the process then uses about 3 GB of memory, so
run one model process at a time. `uv run` installs the dependencies listed
at the top of this file, including the spaCy model that misaki needs.

Usage:
    uv run narrate.py --text "Good evening." --out narration.wav --phones-out phones.json
    uv run narrate.py --selftest            # pure-Python checks, no model needed
    uv run narrate.py --selftest --selftest-synth   # also synthesizes one sentence
Exit code 0 on success; non-zero with a one-line reason on failure.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

KOKORO_REPO = "mlx-community/Kokoro-82M-bf16"

# Calibration of Kokoro's duration grid against the audio, in seconds.
# A running sum of `pred_dur` places every phoneme late by a constant amount:
# on the 47 s bake-off script (voice af_heart, 489 matched phonemes) the
# onsets were a median of 55 ms after Montreal Forced Aligner's, with no
# drift (52 to 60 ms in each 10 s window). Two duration frames (50 ms) are
# subtracted. Kokoro's own word timestamps subtract three frames at the same
# place (`join_timestamps` in mlx_audio/tts/models/kokoro/pipeline.py).
KOKORO_OFFSET = -0.050
DEFAULT_VOICE = "af_heart"
SEED = 0

# Kokoro (misaki, US English) phoneme symbol -> ARPAbet.
MISAKI_TO_ARPABET = {
    "b": "B", "d": "D", "f": "F", "h": "HH", "j": "Y", "k": "K", "l": "L",
    "m": "M", "n": "N", "p": "P", "s": "S", "t": "T", "v": "V", "w": "W",
    "z": "Z", "ɡ": "G", "g": "G", "ŋ": "NG", "ɹ": "R", "r": "R", "ʃ": "SH",
    "ʒ": "ZH", "ð": "DH", "θ": "TH", "ʤ": "JH", "ʧ": "CH",
    "ɾ": "D",    # flap, as in "water": the tongue taps like a short D
    "T": "D",    # misaki's symbol for the American flap
    "ʔ": "T",    # glottal stop, as in "button"
    "ə": "AH", "ᵊ": "AH", "ʌ": "AH", "i": "IY", "u": "UW", "ɑ": "AA",
    "ɔ": "AO", "ɛ": "EH", "ɜ": "ER", "ɚ": "ER", "ɪ": "IH", "ᵻ": "IH",
    "ʊ": "UH", "æ": "AE", "a": "AA", "e": "EH", "o": "OW", "ɒ": "AA",
    "A": "EY", "I": "AY", "W": "AW", "Y": "OY", "O": "OW", "Q": "OW",
}
STRESS_MARKS = {"ˈ": "1", "ˌ": "2"}
VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"}
LENGTH_MARKS = {"ː"}


@dataclass
class Phone:
    start: float
    end: float
    label: str  # ARPAbet with a stress digit on vowels, or "sil"


def kokoro_phones(ps: str, pred_dur, n_samples: int, sr: int, offset: float) -> list[Phone]:
    """Turn one Kokoro chunk's symbols and durations into timed phones.

    `pred_dur[0]` is the start symbol and `pred_dur[-1]` the end symbol; the
    values between them match the characters of `ps` one to one. A stress
    mark's frames go to the vowel that follows it, and a length mark's frames
    go to the vowel before it. Spaces and punctuation become silence.
    `offset` is the chunk's start time in the whole audio.
    """
    dur = [float(d) for d in pred_dur]
    if len(dur) != len(ps) + 2:
        raise ValueError(f"expected {len(ps) + 2} durations, got {len(dur)}")
    frame = n_samples / sr / sum(dur)  # seconds per frame, from the real audio
    phones: list[Phone] = []
    t = offset
    end = t + dur[0] * frame
    phones.append(Phone(t, end, "sil"))
    t = end
    carry = 0.0  # time of a stress mark, waiting for its vowel
    stress = ""
    for ch, d in zip(ps, dur[1:-1]):
        span = d * frame
        if ch in STRESS_MARKS:
            carry += span
            stress = STRESS_MARKS[ch]
            continue
        if ch in LENGTH_MARKS and phones:
            phones[-1].end += span
            t += span
            continue
        label = MISAKI_TO_ARPABET.get(ch, "sil")
        if label in VOWELS:
            # ARPAbet stress digit: 1 primary, 2 secondary, 0 none.
            label += stress or "0"
        start = t
        t += carry + span
        carry, stress = 0.0, ""
        phones.append(Phone(start, t, label))
    phones.append(Phone(t, t + carry + dur[-1] * frame, "sil"))
    return phones


def apply_offset(phones: list[Phone], total: float, offset: float = KOKORO_OFFSET) -> list[Phone]:
    """Shift every phone by `offset`, keep the times inside [0, total], end at `total`."""
    for p in phones:
        p.start = min(total, max(0.0, p.start + offset))
        p.end = min(total, max(0.0, p.end + offset))
    phones[-1].end = total
    return phones


def synthesize_kokoro(text: str, voice: str = DEFAULT_VOICE, speed: float = 1.0):
    """Synthesize `text` with Kokoro-82M. Return (audio float32 array, sample rate, phones, phoneme text)."""
    import mlx.core as mx
    import numpy as np
    from mlx_audio.tts.utils import load_model

    model = load_model(KOKORO_REPO)
    mx.random.seed(SEED)
    pipe = model._get_pipeline("a")  # "a" is American English
    sr = model.config.sample_rate
    parts = []
    phones: list[Phone] = []
    phoneme_text: list[str] = []
    offset = 0.0
    for res in pipe(text, voice=voice, speed=speed, split_pattern=r"\n+"):
        audio = np.asarray(res.audio, dtype=np.float32).reshape(-1)
        pred = np.asarray(res.pred_dur).reshape(-1).tolist()
        phones += kokoro_phones(res.phonemes, pred, len(audio), sr, offset)
        phoneme_text.append(res.phonemes)
        parts.append(audio)
        offset += len(audio) / sr
    if not parts:
        raise RuntimeError("Kokoro returned no audio for this text")
    audio = np.concatenate(parts)
    apply_offset(phones, len(audio) / sr)
    return audio, sr, phones, " ".join(phoneme_text)


def write_outputs(text: str, voice: str, audio, sr: int, phones: list[Phone], wav: Path, phones_out: Path) -> float:
    import numpy as np
    import soundfile as sf

    wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(wav, np.clip(audio, -1, 1), sr, subtype="PCM_16")
    duration = len(audio) / sr
    doc = {"text": text, "duration": duration, "voice": voice,
           "source": f"kokoro pred_dur {KOKORO_OFFSET * 1000:+.0f} ms",
           "phones": [[p.start, p.end, p.label] for p in phones]}  # full precision: frame edges are tie-sensitive
    phones_out.parent.mkdir(parents=True, exist_ok=True)
    phones_out.write_text(json.dumps(doc) + "\n")
    return duration


def selftest(synth: bool = False) -> None:
    # One chunk: "hˈɛlO wˈɜld." with 14 durations (start symbol, 12 symbols, end symbol).
    ps = "hˈɛlO wˈɜld."
    dur = [1, 2, 2, 5, 3, 4, 2, 3, 2, 6, 3, 4, 2, 1]
    assert sum(dur) == 40
    phones = kokoro_phones(ps, dur, n_samples=24000, sr=24000, offset=0.0)  # 25 ms per frame
    assert abs(phones[-1].end - 1.0) < 1e-9, phones[-1]  # total time matches the audio
    assert all(abs(a.end - b.start) < 1e-9 for a, b in zip(phones, phones[1:])), "gap between phones"
    labels = [p.label for p in phones]
    assert labels == ["sil", "HH", "EH1", "L", "OW0", "sil", "W", "ER1", "L", "D", "sil", "sil"], labels
    eh = phones[2]  # the stress mark's 2 frames go to the vowel: 2 + 5 frames
    assert abs((eh.end - eh.start) - 7 * 0.025) < 1e-9, eh
    assert abs((phones[5].end - phones[5].start) - 2 * 0.025) < 1e-9  # the space is silence
    shifted = apply_offset(phones, 1.0)
    assert shifted[1].start == 0.0 and abs(shifted[1].end - 0.025) < 1e-9, shifted[1]  # HH, clamped at 0
    assert abs(shifted[2].start - 0.025) < 1e-9 and abs(shifted[2].end - 0.200) < 1e-9, shifted[2]
    assert shifted[-1].end == 1.0
    # A length mark's frames go to the phone before it.
    lp = kokoro_phones("iː", [1, 2, 3, 1], 24000, 24000, 0.0)
    assert [p.label for p in lp] == ["sil", "IY0", "sil"] and abs(lp[1].end - lp[1].start - 5 / 7) < 1e-9, lp
    try:
        kokoro_phones("ab", [1, 2, 3], 24000, 24000, 0.0)
        raise AssertionError("expected ValueError for a wrong duration count")
    except ValueError:
        pass
    assert KOKORO_OFFSET == -0.050
    print("selftest OK: narrate (pure-Python part)")

    if not synth:
        return
    try:
        import mlx_audio  # noqa: F401
        import numpy  # noqa: F401
        import soundfile  # noqa: F401
    except ImportError as e:
        print(f"SKIP: synthesis needs {e.name}")
        return
    with tempfile.TemporaryDirectory() as tmp:
        audio, sr, ph, _ = synthesize_kokoro("Hello there, my friend.")
        wav, pj = Path(tmp) / "n.wav", Path(tmp) / "p.json"
        dur = write_outputs("Hello there, my friend.", DEFAULT_VOICE, audio, sr, ph, wav, pj)
        doc = json.loads(pj.read_text())
        assert abs(doc["phones"][-1][1] - dur) < 1e-3 and doc["phones"][0][0] == 0.0, doc["phones"][:2]
        assert all(a[1] <= b[1] + 1e-9 for a, b in zip(doc["phones"], doc["phones"][1:]))
        assert wav.stat().st_size > 2 * sr * dur * 0.9
    print("selftest OK: narrate (synthesis)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Kokoro speech synthesis with phoneme timestamps (Apple Silicon).")
    ap.add_argument("--text", help="the text to narrate")
    ap.add_argument("--text-file", type=Path, help="file with the text")
    ap.add_argument("--out", type=Path, help="narration WAV to write")
    ap.add_argument("--phones-out", type=Path, help="phones file to write")
    ap.add_argument("--voice", default=DEFAULT_VOICE, help=f"Kokoro voice (default {DEFAULT_VOICE})")
    ap.add_argument("--speed", type=float, default=1.0, help="speaking speed (default 1.0)")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    ap.add_argument("--selftest-synth", action="store_true", help="with --selftest: also synthesize one sentence")
    a = ap.parse_args(argv)
    if a.selftest:
        selftest(a.selftest_synth)
        return 0
    if not a.out or not a.phones_out or (a.text is None) == (a.text_file is None):
        ap.error("--out, --phones-out and exactly one of --text or --text-file are required")
    try:
        text = " ".join((a.text if a.text is not None else a.text_file.read_text()).split())
        if not text:
            raise ValueError("the text is empty")
        audio, sr, phones, _ = synthesize_kokoro(text, a.voice, a.speed)
        duration = write_outputs(text, a.voice, audio, sr, phones, a.out, a.phones_out)
    except ImportError as e:
        print(f"error: missing package {e.name}; run this script with `uv run`", file=sys.stderr)
        return 1
    except (OSError, ValueError, RuntimeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"{a.out}  {duration:.2f} s, {len(phones)} phones, voice {a.voice}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
