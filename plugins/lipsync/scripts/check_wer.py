#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = [
#   "mlx-audio==0.6.7",
#   "jiwer",
#   "whisper-normalizer",
#   "huggingface_hub",
# ]
# ///
"""Check that a speech recognizer hears the script in a narration.

Whisper large-v3 (MLX, Apple Silicon) transcribes the WAV. The transcript
and the reference text go through Whisper's English text normalizer, and
the word error rate (WER) is computed. Pass: WER under the limit (3%).

Input:  a WAV file and its text.
Output: a JSON result (--out) and a final line "CHECK 2 PASS|FAIL: ...".
        Exit code 0 on pass, 1 on fail.

    uv run check_wer.py narration.wav --text-file script.txt --out wer.json

`mlx-community/whisper-large-v3-mlx` holds weights only, and mlx-audio 0.6.7
fails without tokenizer and processor files ("Processor not found"). This
script links the weights and the JSON and text files of
`openai/whisper-large-v3` into one cache folder
(~/.cache/lipsync/whisper-large-v3-mlx) and loads that.

The first run downloads the model (about 3 GB). Load one model at a time.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

LIMIT = 0.03
CACHE = Path.home() / ".cache" / "lipsync" / "whisper-large-v3-mlx"


def edit_counts(ref: list, hyp: list) -> tuple:
    """Return (substitutions, deletions, insertions) of the best word alignment."""
    n, m = len(ref), len(hyp)
    # cost[i][j] = (edits, subs, dels, ins) for ref[:i] against hyp[:j]
    prev = [(j, 0, 0, j) for j in range(m + 1)]
    for i in range(1, n + 1):
        cur = [(i, 0, i, 0)]
        for j in range(1, m + 1):
            if ref[i - 1] == hyp[j - 1]:
                best = prev[j - 1]
            else:
                s, d, ins = prev[j - 1], prev[j], cur[j - 1]
                best = min(
                    (s[0] + 1, s[1] + 1, s[2], s[3]),
                    (d[0] + 1, d[1], d[2] + 1, d[3]),
                    (ins[0] + 1, ins[1], ins[2], ins[3] + 1),
                )
            cur.append(best)
        prev = cur
    return prev[m][1], prev[m][2], prev[m][3]


def wer_result(ref_words: list, hyp_words: list, limit: float = LIMIT) -> dict:
    subs, dels, ins = edit_counts(ref_words, hyp_words)
    wer = (subs + dels + ins) / max(1, len(ref_words))
    return {"wer": round(wer, 4), "words": len(ref_words), "substitutions": subs,
            "deletions": dels, "insertions": ins, "limit": limit, "pass": wer < limit}


def whisper_dir() -> Path:
    """Return a folder with the MLX weights and the processor files."""
    from huggingface_hub import snapshot_download

    if (CACHE / "weights.npz").exists() and (CACHE / "tokenizer.json").exists():
        return CACHE
    CACHE.mkdir(parents=True, exist_ok=True)
    weights = Path(snapshot_download("mlx-community/whisper-large-v3-mlx"))
    proc = Path(snapshot_download("openai/whisper-large-v3", allow_patterns=["*.json", "*.txt"]))
    for src in list(proc.iterdir()) + list(weights.iterdir()):  # the weights' config.json wins
        if src.is_file() or src.is_symlink():
            link = CACHE / src.name
            if link.is_symlink() or link.exists():
                link.unlink()
            link.symlink_to(src.resolve())
    return CACHE


def transcribe(wav: Path) -> str:
    from mlx_audio.stt.utils import load_model

    model = load_model(str(whisper_dir()))
    r = model.generate(str(wav), language="en", temperature=0.0,
                       condition_on_previous_text=False, verbose=False)
    return (r.text if hasattr(r, "text") else r["text"]).strip()


def selftest() -> None:
    ref = "the map moves when you blink".split()
    assert edit_counts(ref, ref) == (0, 0, 0)
    assert edit_counts(ref, "the map moved when you blink".split()) == (1, 0, 0)
    assert edit_counts(ref, "the map when you blink".split()) == (0, 1, 0)
    assert edit_counts(ref, "the old map moves when you blink".split()) == (0, 0, 1)
    r = wer_result(ref, "a map moves when you".split())
    assert (r["substitutions"], r["deletions"], r["insertions"]) == (1, 1, 0), r
    assert r["wer"] == round(2 / 6, 4) and r["pass"] is False
    assert wer_result(["a"] * 100, ["a"] * 98 + ["b", "b"])["pass"] is True   # 2% passes
    assert wer_result(["a"] * 100, ["a"] * 97 + ["b"] * 3)["pass"] is False   # 3% does not
    try:
        from whisper_normalizer.english import EnglishTextNormalizer
        norm = EnglishTextNormalizer()
        assert norm("Good evening, Mr. Baker!") == norm("good evening mister baker")
    except ImportError:
        print("SKIP: the text normalizer test needs whisper-normalizer")
    print("selftest OK (the transcription itself needs mlx-audio and is not run here)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("wav", nargs="?", type=Path)
    ap.add_argument("--text")
    ap.add_argument("--text-file", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--limit", type=float, default=LIMIT, help="pass when WER is under this (default 0.03)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if a.wav is None or (a.text is None) == (a.text_file is None):
        ap.error("give a WAV file and exactly one of --text and --text-file")
    text = a.text if a.text is not None else a.text_file.read_text()

    from whisper_normalizer.english import EnglishTextNormalizer

    norm = EnglishTextNormalizer()
    hyp = transcribe(a.wav)
    result = wer_result(norm(text).split(), norm(hyp).split(), a.limit)
    result.update({"wav": str(a.wav), "transcript": hyp})
    print(json.dumps(result, indent=1, ensure_ascii=False))
    print(f"CHECK 2 {'PASS' if result['pass'] else 'FAIL'}: WER = {result['wer']:.2%} (limit under {a.limit:.0%})")
    if a.out:
        a.out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
