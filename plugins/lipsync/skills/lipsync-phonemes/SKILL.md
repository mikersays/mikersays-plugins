---
name: lipsync-phonemes
description: Get the start and end time of every phoneme in a speech recording, as ARPAbet labels, by forced alignment with Montreal Forced Aligner (or from a TTS model's own durations), and judge how far to trust the times. Trigger on "phoneme timestamps", "forced alignment", "align this audio with its transcript", "when is each phoneme spoken", or "set up Montreal Forced Aligner".
argument-hint: "[audio.wav] [transcript]"
allowed-tools: Bash, Read, Write
---

# lipsync-phonemes: phoneme timestamps from audio

This skill does one job: produce `phones.json`, the timed phonemes of one
speech recording, from the audio and its transcript.

```json
{"text": "...", "duration": 13.18, "source": "mfa english_us_arpa",
 "phones": [[0.30, 0.36, "G"], [0.36, 0.41, "UH1"], ...],
 "words": [{"start": 0.30, "end": 0.45, "word": "good"}, ...],
 "unknown_words": [], "onset_check": {"onsets": 6, "median_word_start_minus_onset_ms": -25.0, "suspect": false}}
```

## Choose the source

| Source | Use it when | Accuracy measured |
|---|---|---|
| The TTS model's durations | The audio comes from Kokoro (`lipsync-narrate` writes `phones.json` itself) | Median 15 ms from MFA, 90th percentile 45 ms, after a constant -50 ms offset |
| Montreal Forced Aligner (MFA) | Any other audio with a transcript: another TTS model or a recording | Onsets a median of 20 ms before the waveform onset (17 onsets after pauses) |
| WhisperX | Never for phonemes | It returns words and characters only, a median of 39 ms after the waveform onset |

## Locate the script

```bash
LS="$CLAUDE_PLUGIN_ROOT/scripts"
[ -f "$LS/align_mfa.py" ] || LS="$(find ~/.claude/plugins ~/.codex/plugins -type d -path '*/lipsync/scripts' -print -quit 2>/dev/null)"
[ -f "$LS/align_mfa.py" ] && echo "scripts: $LS" || echo "lipsync scripts not found"
```

If this prints "lipsync scripts not found", the plugin is not installed
where expected; report that and stop.

## Install MFA once

MFA needs conda packages (Kaldi); pip alone does not work.

```bash
python3 "$LS/align_mfa.py" --install --mfa-env ./.mfa    # prints the four commands with absolute paths
command -v micromamba >/dev/null || brew install micromamba
MAMBA_ROOT_PREFIX="$PWD/.mfa-pkgs" micromamba create -y -p "$PWD/.mfa" -c conda-forge montreal-forced-aligner python=3.11
MFA_ROOT_DIR="$PWD/.mfa/root" ./.mfa/bin/mfa model download acoustic english_us_arpa
MFA_ROOT_DIR="$PWD/.mfa/root" ./.mfa/bin/mfa model download dictionary english_us_arpa
```

- Creating the environment took 20 s and the two model downloads 11 s on a
  fast connection.
- The environment is 1.4 GB with the models (MFA 3.4.4). `MAMBA_ROOT_PREFIX`
  keeps micromamba's package cache (533 MB) in `.mfa-pkgs/` next to it,
  not in the home folder; delete that folder after the install if you want
  the space back.
- Add `.mfa/` and `.mfa-pkgs/` to `.gitignore`.
- Set `MFA_ENV` to reuse one environment across projects.

## Align

```bash
python3 "$LS/align_mfa.py" --wav narration.wav --text-file script.txt --out phones.json --mfa-env ./.mfa
```

A 47 s file takes about 40 s and a 10 s file 36 s: most of the time is
MFA's start-up. The script uses wide beams (`--beam 100 --retry_beam 400`)
so that MFA does not drop a long single file. After each run it deletes
MFA's working copy of the corpus (`.mfa/root/corpus`, 0.25 to 0.4 GB).

The script prints the phone count, any unknown words, and the onset check
(see "Check the times").

## Read the result with care

- **Unknown words.** MFA labels a word outside its dictionary as `spn`
  ("spoken noise") and gives it no phonemes: the word appears in `phones`
  as one entry with the label `spn`. The script lists these words in
  `unknown_words`. `spn` is speech, not silence: a first version of the
  frame plan treated it as silence and closed the mouth through the word
  "Psst". Respell the word in the transcript, or accept a generic open mouth.
- **Silence.** MFA writes no entry for a pause; a gap between two phones is
  the pause.
- **Stops.** MFA puts the silent closure of p, b, t, d, k, g inside the
  consonant's interval.
- **Two aligners do not agree to 40 ms.** MFA and WhisperX word onsets
  differed by a median of 52 ms on a 47 s script (159 words; 47, 61, and
  48.5 ms on three shorter clips). WhisperX was later every time. Against
  the waveform, MFA was 20 ms early and WhisperX 39 ms late. Use MFA as the
  reference, and do not average the two.
- **Model durations stretch phrase ends.** Kokoro gives the last phoneme
  before a pause up to 330 ms of the pause. Detect silence from the audio
  (the `lipsync-plan` skill does) instead of trusting those ends.

## Check the times

The script does this check on every run and stores it as `onset_check`.
After a pause of 150 ms or more (the start of the file counts), the first
5 ms step whose level rises above -40 dBFS is an onset that no aligner
produced. The script compares each such onset with the nearest word start
and prints the median of (word start - onset):

```text
onset check: 17 onsets after pauses, word start - waveform onset: median -20.0 ms (min -55.0, max -5.0)
```

Measured on Kokoro speech: -20.0 ms on a 47 s script (17 onsets) and
-20.0 ms on a 10 s clip (4 onsets). A median beyond 30 ms either way prints
`SUSPECT`; so does nothing else, so also distrust a sign that flips between
files. With fewer than 3 onsets the median says little. The check needs a
16-bit PCM WAV.

## Tested on, and not

Tested: MFA 3.4.4 with `english_us_arpa` on Kokoro speech, 24 kHz mono, 12
to 47 s, clean audio, on macOS (Apple Silicon). Not tested: human
recordings, noise or music, other languages and dictionaries, files over
60 s, and Linux.
