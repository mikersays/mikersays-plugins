#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Phoneme timestamps from audio with Montreal Forced Aligner (MFA).

Stdlib only; it calls the `mfa` binary of a conda environment. MFA aligns a
WAV file and its transcript with the `english_us_arpa` acoustic model and
dictionary and returns ARPAbet phonemes with start and end times.

Inputs: `--wav audio.wav` and the transcript (`--text "..."` or
`--text-file f.txt`). Output (`--out phones.json`): a phones file,
`{"text", "duration", "source", "phones": [[start, end, label], ...],
"unknown_words": [...]}`. A word that the MFA dictionary lacks comes back
as one `spn` phone; `unknown_words` lists those words, because the mouth
shows a generic half-open shape for them (add the word to a custom
dictionary if the shape matters).

The MFA environment is the conda prefix given by `--mfa-env`, else
`$MFA_ENV`, else `./.mfa`. `--install` prints the commands that create it;
it does not run them.

Usage:
    uv run align_mfa.py --wav narration.wav --text-file narration.txt --out phones.json
    uv run align_mfa.py --install
    uv run align_mfa.py --selftest
Exit code 0 on success; non-zero with a one-line reason on failure.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

MFA_MODEL = "english_us_arpa"


def default_env() -> Path:
    return Path(os.environ.get("MFA_ENV") or ".mfa").expanduser().resolve()


def install_commands(env: Path) -> list[str]:
    """Return the shell commands that install MFA into the conda prefix `env`."""
    return [
        "brew install micromamba",
        f"micromamba create -y -p {env} -c conda-forge montreal-forced-aligner python=3.11",
        f"MFA_ROOT_DIR={env}/root {env}/bin/mfa model download acoustic {MFA_MODEL}",
        f"MFA_ROOT_DIR={env}/root {env}/bin/mfa model download dictionary {MFA_MODEL}",
    ]


def parse_mfa_json(doc: dict) -> tuple[list[list], list[dict], list[str]]:
    """Turn MFA's JSON output into (phones, words, unknown words).

    `doc["tiers"]["phones"]["entries"]` and `["words"]["entries"]` hold
    [start, end, label] triples. An empty phone label is silence. A word is
    unknown when a `spn` phone lies inside it.
    """
    tiers = doc["tiers"]
    phones = [
        [float(s), float(e), "sil" if not str(label).strip() else str(label)]
        for s, e, label in tiers["phones"]["entries"]
    ]
    words = [
        {"start": float(s), "end": float(e), "word": w}
        for s, e, w in tiers["words"]["entries"] if str(w).strip()
    ]
    unknown: list[str] = []
    for w in words:
        mid_hit = any(
            lab == "spn" and s >= w["start"] - 1e-6 and e <= w["end"] + 1e-6
            for s, e, lab in phones
        )
        if mid_hit and w["word"] not in unknown:
            unknown.append(w["word"])
    return phones, words, unknown


def mfa_align(wav: Path, text: str, env: Path, beam: int = 100, retry_beam: int = 400) -> dict:
    """Align one WAV file with its transcript.

    Returns {"phones": [[s, e, label], ...], "words": [...], "unknown_words": [...]}.
    The wide beams keep MFA from dropping a long single-file utterance.
    """
    mfa = env / "bin" / "mfa"
    if not mfa.exists():
        raise RuntimeError(f"MFA is not installed at {env}; run with --install to see the commands")
    run_env = dict(os.environ)
    run_env["MFA_ROOT_DIR"] = str(env / "root")
    run_env["PATH"] = f"{env / 'bin'}:{run_env['PATH']}"
    with tempfile.TemporaryDirectory(prefix="mfa-") as tmp:
        corpus = Path(tmp) / "corpus"
        out = Path(tmp) / "out"
        corpus.mkdir()
        shutil.copy(wav, corpus / "utt.wav")
        (corpus / "utt.lab").write_text(text.strip() + "\n")
        cmd = [
            str(mfa), "align", str(corpus), MFA_MODEL, MFA_MODEL, str(out),
            "--clean", "--single_speaker", "--output_format", "json",
            "--beam", str(beam), "--retry_beam", str(retry_beam),
            "--num_jobs", "2", "--no_use_mp",
        ]
        run = subprocess.run(cmd, env=run_env, capture_output=True, text=True)
        result = out / "utt.json"
        if run.returncode != 0 or not result.exists():
            raise RuntimeError(f"mfa align failed: {(run.stdout[-500:] + run.stderr[-500:]).strip()}")
        doc = json.loads(result.read_text())
    phones, words, unknown = parse_mfa_json(doc)
    return {"phones": phones, "words": words, "unknown_words": unknown}


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


# A small sample of MFA's JSON output ("psst" is not in the dictionary).
SAMPLE = {"tiers": {
    "words": {"type": "interval", "entries": [
        [0.03, 0.30, "so"], [0.30, 0.55, "psst"], [0.55, 0.62, ""], [0.62, 0.95, "hello"]]},
    "phones": {"type": "interval", "entries": [
        [0.03, 0.15, "S"], [0.15, 0.30, "OW1"], [0.30, 0.55, "spn"], [0.55, 0.62, ""],
        [0.62, 0.70, "HH"], [0.70, 0.78, "AH0"], [0.78, 0.86, "L"], [0.86, 0.95, "OW1"]]},
}}


def selftest() -> None:
    phones, words, unknown = parse_mfa_json(SAMPLE)
    assert len(phones) == 8 and phones[3] == [0.55, 0.62, "sil"], phones
    assert [w["word"] for w in words] == ["so", "psst", "hello"], words
    assert unknown == ["psst"], unknown
    assert phones[2][2] == "spn"
    cmds = install_commands(Path("/x/.mfa"))
    assert cmds[0] == "brew install micromamba" and "montreal-forced-aligner" in cmds[1]
    assert cmds[2].startswith("MFA_ROOT_DIR=/x/.mfa/root /x/.mfa/bin/mfa model download acoustic")
    try:
        mfa_align(Path("none.wav"), "x", Path("/nonexistent-mfa-env"))
        raise AssertionError("expected an error for a missing environment")
    except RuntimeError as e:
        assert "not installed" in str(e)
    print("selftest OK: align_mfa")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Phoneme timestamps from audio with Montreal Forced Aligner.")
    ap.add_argument("--wav", type=Path, help="audio file to align")
    ap.add_argument("--text", help="transcript of the audio")
    ap.add_argument("--text-file", type=Path, help="file with the transcript")
    ap.add_argument("--out", type=Path, help="phones file to write")
    ap.add_argument("--mfa-env", type=Path, help="conda env prefix of MFA (default: $MFA_ENV, else ./.mfa)")
    ap.add_argument("--install", action="store_true", help="print the install commands and exit")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    a = ap.parse_args(argv)

    env = (a.mfa_env.expanduser().resolve() if a.mfa_env else default_env())
    if a.selftest:
        selftest()
        return 0
    if a.install:
        print("\n".join(install_commands(env)))
        return 0
    if not a.wav or not a.out or (a.text is None) == (a.text_file is None):
        ap.error("--wav, --out and exactly one of --text or --text-file are required")
    try:
        text = " ".join((a.text if a.text is not None else a.text_file.read_text()).split())
        res = mfa_align(a.wav, text, env)
        duration = wav_duration(a.wav)
    except (OSError, RuntimeError, wave.Error, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    doc = {"text": text, "duration": round(duration, 6), "source": f"mfa {MFA_MODEL}",
           "phones": [[round(s, 4), round(e, 4), lab] for s, e, lab in res["phones"]],
           "unknown_words": res["unknown_words"]}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(doc) + "\n")
    msg = f"{a.out}  {len(doc['phones'])} phones, {duration:.2f} s"
    if res["unknown_words"]:
        msg += f"; unknown words (spn): {', '.join(res['unknown_words'])}"
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
