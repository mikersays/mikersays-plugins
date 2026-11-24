---
name: lipsync-narrate
description: Narrate text to a WAV file with a local text-to-speech model on Apple Silicon (Kokoro-82M through mlx-audio) and get the timing of every phoneme with it, or run a measured bake-off to choose a different local model. Trigger on "narrate this text locally", "local TTS on my Mac", "text to speech with phoneme timing", "which local TTS model should I use", or "run a TTS bake-off".
argument-hint: "[text or text file] [--voice af_heart]"
allowed-tools: Bash, Read, Write
---

# lipsync-narrate: local narration with phoneme timing

This skill does one job: turn text into speech on an Apple Silicon Mac, with
no cloud service, and return the phoneme times that the model used. The
default model is Kokoro-82M, chosen by the bake-off below.

## Locate the scripts

```bash
LS="$CLAUDE_PLUGIN_ROOT/scripts"
[ -f "$LS/narrate.py" ] || LS="$(find ~/.claude/plugins ~/.codex/plugins -type d -path '*/lipsync/scripts' -print -quit 2>/dev/null)"
[ -f "$LS/narrate.py" ] && echo "scripts: $LS" || echo "lipsync scripts not found"
```

If this prints "lipsync scripts not found", the plugin is not installed
where expected; report that and stop.

The scripts need `uv` (`brew install uv`).

## Narrate

```bash
uv run "$LS/narrate.py" --text-file script.txt --out narration.wav --phones-out phones.json --voice af_heart
```

- `narration.wav`: mono, 24 kHz, 16-bit.
- `phones.json`: `{"text", "duration", "voice", "source", "phones": [[start, end, label], ...]}`.
  Labels are ARPAbet with a stress digit on vowels (`AH0`, `IY1`), and `sil`
  for silence. The list starts and ends with `sil`, and two `sil` entries
  can follow each other (a space, then a punctuation mark). Times are
  full-precision floats such as `0.39999999999999997`; do not round them,
  because a rounded time can move a phoneme across a frame edge.
- The first run downloads the model (`mlx-community/Kokoro-82M-bf16`) to
  `~/.cache/huggingface/hub`. The full repository with its 54 voices is
  339 MB. `uv` keeps the Python packages in `~/.cache/uv`. Both caches are
  outside the project folder and are shared between projects.
- Voices tested: `af_heart` (woman), `am_michael` (man), `am_puck` (man,
  lighter). The voice name's first letter sets the accent: `a` is American.

Where the times come from: Kokoro predicts a duration for every input symbol
(`pred_dur`, in frames of 25 ms), and its decoder makes exactly that much
audio. So the times describe the audio, not a guess from the text. The
script subtracts a constant 50 ms, because a running sum of `pred_dur` was a
median of 55 ms late against Montreal Forced Aligner on a 47 s script (489
phonemes, 52 to 60 ms in every 10 s window, so no drift). After the offset,
the median absolute difference was 15 ms and the 90th percentile 45 ms.

Hand `phones.json` and the WAV to the `lipsync-plan` skill. Kokoro stretches
the last phoneme of a phrase across the pause that follows (up to 330 ms
measured); `lipsync-plan` corrects that from the audio, so do not skip its
`--wav` input.

## Verify the narration

```bash
uv run "$LS/check_wer.py" narration.wav --text-file script.txt --out wer.json
```

Whisper large-v3 transcribes the WAV, and both texts go through Whisper's
English normalizer. The script prints `CHECK 2 PASS` when the word error
rate is under 3% (exit code 0). This checks the words only, not the phoneme
times; the closed-mouth check of `lipsync-plan` is the timing check. The
first run downloads about 3 GB. Measured
on Kokoro: 0.00% on a 159-word script, and 2.22%, 0.00%, and 2.63% on three
clips of about 40 words. In a short clip one misheard word is already over
2%, so judge a voice on at least 100 words, and avoid invented names in a
short test text.

## Memory rules

- Load one model at a time, each in its own process.
- Before a run: `memory_pressure | tail -1` and `sysctl vm.swapusage`. Under
  30% free, wait. Only `tts_bakeoff.py` enforces this itself; before
  `narrate.py` and `check_wer.py`, check by hand. Swap that is already in
  use and does not grow is not a reason to wait.
- Kokoro's peak MLX memory was 2.84 GB, but its process footprint reached
  12.15 GB, because MLX keeps a buffer cache.

## Bake-off result (2026-11-22, Apple M6, 32 GB, mlx-audio 0.6.7)

The test used one fixed 159-word script and ran one model at a time:

| Model | License | Commercial use | RTF | Peak MLX | Peak footprint | WER | UTMOS | Phoneme times |
|---|---|---|---|---|---|---|---|---|
| Kokoro-82M | Apache-2.0 | yes | 0.041 | 2.84 GB | 12.15 GB | 0.0% | 4.52 | yes |
| Chatterbox | MIT | yes | 0.694 | 4.93 GB | 8.98 GB | 1.3% | 3.99 | no |
| Chatterbox Turbo | MIT | yes | 0.352 | 4.76 GB | 11.16 GB | 0.0% | 4.44 | no |
| Dia-1.6B | Apache-2.0 | yes | 3.928 | 15.65 GB | 25.63 GB | 19.5% | 3.68 | no |
| VibeVoice-1.5B | MIT tag, research-only card | no | 0.706 | 5.64 GB | 6.14 GB | 0.0% | 4.31 | no |
| VibeVoice-Realtime-0.5B | MIT tag, research-only card | no | 0.756 | 6.59 GB | 17.79 GB | 0.0% | 4.15 | no |
| Fish Audio S2 Pro 8-bit | research license | no | 1.609 | 12.42 GB | 26.79 GB | 0.0% | 4.41 | no |

RTF is synthesis time over audio time (lower is faster). WER is Whisper
large-v3 against the script. UTMOS is a predicted opinion score from 1 to 5,
not a listening test. Nobody listened to the samples for the choice: it
rests on UTMOS, WER, the license, and Kokoro being the only model that
returns phoneme times. Chatterbox Turbo is the runner-up; it needs a forced
aligner (`lipsync-phonemes`).

## Run your own bake-off

Use this when the user wants another model or a newer one.

1. Write one fixed script of about 60 s (about 160 words). Spell numbers
   out, so that the word error rate is fair.
2. For each model, in sequence:

   ```bash
   uv run "$LS/tts_bakeoff.py" --repo <hf repo> --text-file script.txt \
       --out samples/<key>.wav --json runs/<key>.json [--voice V] [--max-chars 300] [--prefix "[S1] "]
   ```

   The script refuses to start under 30% free memory (`--force` overrides)
   and records load time, synthesis time, RTF, the MLX peak, and the max
   RSS. For the process's "peak memory footprint", which was 1.1 to 4.3 times
   the MLX peak, run the script with a venv's own interpreter under
   `/usr/bin/time -l`. Wrapping `uv run` measures uv, not the model.
3. Check every sample for completeness with a speech recognizer before you
   compare quality. Two models dropped the end of the script (see below).
4. Record the license from the model card, not only from the license tag.
5. Pick the best-sounding model whose license fits the use. State what the
   judgment rests on, and keep the samples so a person can listen.

## Failures and gotchas

- **Dia-1.6B** garbled its last chunk and lost 31 words. Its footprint of
  25.63 GB pushed a 32 GB machine's swap use from 1.1 GB to 6.9 GB. Do not
  run it beside other work on 32 GB.
- **Fish S2 Pro** stopped 14 words early with the default `max_tokens=1024`
  on the whole script. Sentence chunks and `max_tokens=2048` fixed it.
- **Chatterbox** needs chunks of about 300 characters.
  `mlx-community/Chatterbox-TTS-fp16` has no built-in voice;
  `mlx-community/chatterbox-fp16` has one.
- **VibeVoice** carries an MIT tag, but its card limits it to research.
- `mlx-community/whisper-large-v3-mlx` has no processor files, and mlx-audio
  0.6.7 then fails with "Processor not found". `check_wer.py` links the JSON
  and text files of `openai/whisper-large-v3` next to the weights.
- Short invented words fail speech recognition: Whisper heard "Wren" as
  "Ren" and "Psst" as "St.", one word error each in clips of about 40 words.
- Larger models exist that were not run: Fish Audio Drama 3 led the
  Artificial Analysis open-weights list on 2026-11-22, but its 3-bit MLX build
  needs 22.5 to 24 GB by its documentation.

## Tested on, and not

Tested: macOS on an Apple M6 with 32 GB, mlx-audio 0.6.7, Python 3.12,
American English, texts of 12 to 47 s, speed 1.0, the three voices above.
Not tested: other languages, other speeds, texts over 60 s, Intel Macs,
Linux, and voice cloning.
