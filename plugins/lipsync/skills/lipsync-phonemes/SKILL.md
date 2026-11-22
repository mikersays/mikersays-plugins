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
 "phones": [[0.30, 0.36, "G"], [0.36, 0.41, "UH1"], ...], "unknown_words": []}
```

## Choose the source

| Source | Use it when | Accuracy measured |
|---|---|---|
| The TTS model's durations | The audio comes from Kokoro (`lipsync-narrate` writes `phones.json` itself) | Median 15 ms from MFA, 90th percentile 45 ms, after a constant -50 ms offset |
| Montreal Forced Aligner (MFA) | Any other audio with a transcript: another TTS model or a recording | Onsets a median of 20 ms before the waveform onset (17 onsets after pauses) |
| WhisperX | Never for phonemes | It returns words and characters only, a median of 39 ms after the waveform onset |

## Locate the script

```bash
LS="${CLAUDE_PLUGIN_ROOT}/scripts"
[ -f "$LS/align_mfa.py" ] || LS="$(dirname "$(find ~/.claude/plugins ~/.codex/plugins -path '*/lipsync/scripts/align_mfa.py' -print -quit 2>/dev/null)")"
```

## Install MFA once

MFA needs conda packages (Kaldi); pip alone does not work.

```bash
python3 "$LS/align_mfa.py" --install --mfa-env ./.mfa    # prints the commands below
brew install micromamba
micromamba create -y -p ./.mfa -c conda-forge montreal-forced-aligner python=3.11
MFA_ROOT_DIR=./.mfa/root ./.mfa/bin/mfa model download acoustic english_us_arpa
MFA_ROOT_DIR=./.mfa/root ./.mfa/bin/mfa model download dictionary english_us_arpa
```

The environment is 1.4 GB (MFA 3.4.4). Keep it out of git. Set `MFA_ENV` to
reuse one environment across projects.

## Align

```bash
python3 "$LS/align_mfa.py" --wav narration.wav --text-file script.txt --out phones.json --mfa-env ./.mfa
```

A 47 s file takes about 40 s. The script uses wide beams (`--beam 100
--retry_beam 400`) so that MFA does not drop a long single file.

## Read the result with care

- **Unknown words.** MFA labels a word outside its dictionary as `spn`
  ("spoken noise") and gives it no phonemes. The script lists these words in
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

After a pause of 150 ms or more, the first 5 ms frame above -40 dBFS is an
onset that no aligner produced. Compare the aligner's word starts with
those onsets. A median beyond 30 ms, or a sign that flips between clips,
means the alignment is wrong for that file.

## Tested on, and not

Tested: MFA 3.4.4 with `english_us_arpa` on Kokoro speech, 24 kHz mono, 12
to 47 s, clean audio, on macOS (Apple Silicon). Not tested: human
recordings, noise or music, other languages and dictionaries, files over
60 s, and Linux.
