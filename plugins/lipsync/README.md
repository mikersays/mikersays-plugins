# lipsync

Make a pixel-art character speak in sync with real audio. The mouth follows
the sound: the plugin takes phoneme times from the audio (or from the model
that made it), not from the letters of the text.

The five skills are the steps of one pipeline. Each does one job and works
alone. The following table summarizes them:

| Skill | Job | Script | Needs |
|---|---|---|---|
| `/lipsync-narrate` | Text to a WAV file and phoneme times, with a local model on Apple Silicon. Holds the model bake-off and its method. | `narrate.py`, `check_wer.py`, `tts_bakeoff.py` | `uv`, Apple Silicon |
| `/lipsync-phonemes` | Phoneme times for any speech audio with a transcript, by forced alignment. | `align_mfa.py` | Montreal Forced Aligner (micromamba) |
| `/lipsync-plan` | Phoneme times to one mouth shape per video frame, and a check that counts open mouths on p, b, m and on pauses. | `viseme_plan.py`, `check_closures.py` | Python 3.9+, `ffmpeg` for the check |
| `/lipsync-sheet` | A 12-shape mouth sheet from the PixelLab MCP server, labeled by eye and cleaned so that only the mouth changes. | `viseme_sheet.py` | `uv`, PixelLab MCP |
| `/lipsync-clip` | Sheet, plan, and audio to an MP4 or a web player that follows `audio.currentTime`. | `render_clip.py` | `ffmpeg` |

## The pipeline

```text
text ──narrate──> narration.wav + phones.json ──plan──> plan.json ──clip──> clip.mp4 / web player
                        │                                  ▲                     │
   other audio ──phonemes──> phones.json ──────────────────┘                     │
   PixelLab ──sheet──> neutral.png (12 cells) ───────────────────────────────────┘
                                 check_closures.py reads clip.mp4 back and counts misses
```

## Files the steps share

- `phones.json`: `{"text", "duration", "source", "phones": [[start, end, label], ...]}`.
  Labels are ARPAbet with a stress digit on vowels, `sil` for silence, and
  `spn` for a word the aligner does not know.
- `plan.json`: `fps`, `duration`, `shapes`, `frames` (one shape name per
  frame), `runs`, `closed_shapes`, `cell`, `background`, `text`, and the phones and
  silences it was built from.
- A sheet: a horizontal PNG strip of 12 square cells in the order `rest`,
  `closed`, `small_open`, `medium_open`, `wide_open`, `smile`,
  `round_small`, `pucker`, `teeth`, `hiss`, `tongue`, `jaw_drop`.

## Scripts

Every script is one file in `scripts/`, runs outside any project, and has a
`--selftest`. `viseme_plan.py`, `check_closures.py`, `render_clip.py`, and
`align_mfa.py` use only the standard library. `narrate.py`,
`check_wer.py`, `tts_bakeoff.py`, and `viseme_sheet.py` carry their
dependencies in a PEP 723 header, so `uv run <script>` installs them on first use.

## Where this came from

The skills record what the pixel-narrator project measured on 2026-11-22 on
an Apple M6 with 32 GB: a bake-off of seven model rows, the timing of
Kokoro's durations against Montreal Forced Aligner, the closed-mouth check
on five clips, and seven PixelLab mouth sheets. Each skill ends with what it
was tested on and what it was not. The project's own copy of this code is
the `narrator/` package of `mikersays/pixel-narrator`; its
`checks/check_plugin_parity.py` fails when the two copies produce different
frame plans.
