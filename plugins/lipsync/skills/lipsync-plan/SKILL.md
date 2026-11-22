---
name: lipsync-plan
description: Turn timed phonemes and the audio into a viseme frame plan, one mouth shape per video frame, with a published phoneme-to-viseme table, coarticulation rules, closed lips on p, b, m and on silence, and an independent check that counts misses in a rendered clip. Trigger on "viseme frame plan", "phonemes to visemes", "lip sync timeline", "mouth shapes from phonemes", "coarticulation", or "check the lip sync".
argument-hint: "[phones.json] [audio.wav] [--fps 24]"
allowed-tools: Bash, Read, Write
---

# lipsync-plan: phoneme timestamps to a frame plan

This skill does one job: decide which mouth shape is on screen in every
video frame. Input: `phones.json` (from `lipsync-narrate` or
`lipsync-phonemes`) and the WAV. Output: `plan.json`.

## Locate the scripts

```bash
LS="$CLAUDE_PLUGIN_ROOT/scripts"
[ -f "$LS/viseme_plan.py" ] || LS="$(find ~/.claude/plugins ~/.codex/plugins -type d -path '*/lipsync/scripts' -print -quit 2>/dev/null)"
[ -f "$LS/viseme_plan.py" ] && echo "scripts: $LS" || echo "lipsync scripts not found"
```

If this prints "lipsync scripts not found", the plugin is not installed
where expected; report that and stop.

Both scripts use only the Python standard library; the check also needs
`ffmpeg` and `ffprobe`.

## Build the plan

```bash
python3 "$LS/viseme_plan.py" --phones phones.json --wav narration.wav --fps 24 --out plan.json
python3 "$LS/viseme_plan.py" --table      # the phoneme -> viseme -> shape table
```

The file names are examples; give the paths of your own files.

`plan.json` holds `fps`, `duration`, `shapes` (the 12 shape names in sheet
order), `frames` (one shape name per frame), `runs`, `closed_shapes`, the
phones, and the measured silences. Frame `k` is on screen from `k/fps` to
`(k+1)/fps`. The number of frames is the duration times the frame rate,
rounded up, so the last frame can be partial. Use 12 to 24 fps; both passed
the check.

Terms used below:

- A **closed frame** shows `rest` or `closed` (the plan's `closed_shapes`).
- A frame is **on screen during** a phoneme when its time span overlaps the
  phoneme's, by any amount.
- A **pause** is a measured silence: an entry of the plan's `silences`
  (100 ms or more). The `sil` entries of `phones.json` are mostly shorter
  gaps between words and do not close the mouth by themselves.

## The mapping

ARPAbet phoneme, then Oculus viseme, then mouth shape.

The viseme set is the 15 visemes of the Oculus Lipsync "Viseme Reference"
(https://developers.meta.com/horizon/documentation/unity/audio-ovrlipsync-viseme-reference/,
read 2026-11-22): sil, PP, FF, TH, DD, kk, CH, SS, nn, RR, aa, E, I, O, U.
The page gives phonemes or example words for 24 of the 39 ARPAbet phonemes.
The other 15 (ZH, NG, HH, W, Y, ER, AE, AH, AO, IY, UW, EY, AY, AW, OY) are
this skill's own choices, marked `extended` in `--table`.

| Viseme | Phonemes | Shape |
|---|---|---|
| sil | silence | `rest` |
| PP | P B M | `closed` |
| FF | F V | `teeth` |
| TH | TH DH | `tongue` |
| DD | T D | `small_open` |
| kk | K G NG | `medium_open` |
| CH | CH JH SH ZH | `hiss` |
| SS | S Z | `hiss` |
| nn | N L | `small_open` |
| RR | R ER | `round_small` |
| aa | AA AE AH | `wide_open` |
| E | EH | `medium_open` |
| I | IH IY Y | `smile` |
| O | AO | `round_small` |
| U | UH UW W | `pucker` |

Diphthongs take two visemes: OW is O then U, EY is E then I, AY is aa then
I, AW is aa then U, OY is O then I. The first gets 55% of the time.

The table uses 9 of the 12 shapes. `rest` comes from silence (rule 0),
`closed` from P, B, M, and `jaw_drop` only from rule 2.

The 12 shapes are the mouth positions of PixelLab
`create_vocal_animation(viseme_count=12)`. For another sheet, pass
`--shape-map overrides.json` (`{"FF": "your_shape", ...}`).

## The rules, in order

0. Where the audio is silent (35 dB below its loudest 10 ms, for 100 ms or
   more), the phonemes give way to silence. Kokoro stretches a phrase's
   last phoneme across the pause; before this rule the mouth stayed open
   through up to 330 ms of silence. These stretches start 15 to 60 ms
   before the aligner's pause and end 5 to 45 ms after it.
1. A pause shorter than 100 ms does not close the mouth.
2. HH takes the shape of the next phoneme. A schwa (`AH0`) is half open. An
   open vowel with primary stress (`AA1`, `AE1`, `AW1`, `AY1`) takes
   `jaw_drop`.
3. A viseme shorter than one frame merges into its longer neighbor. Lip
   closures and pauses are exempt.
4. Each frame shows the shape that covers most of it.
5. Every P, B, and M gets at least one closed frame on screen: if none of
   its frames shows `rest` or `closed`, the frame at its midpoint becomes
   `closed`. A P, B, or M next to a pause can be covered by the pause's
   `rest` frame. Every frame whose center lies in a pause shows `rest`.
   These win over rule 4.

## Check a rendered clip

```bash
python3 "$LS/align_mfa.py" --wav narration.wav --text-file script.txt --out reference.json --mfa-env ./.mfa
python3 "$LS/check_closures.py" clip.mp4 --sheet sheet.png --plan plan.json --phones reference.json
```

The check trusts neither the plan nor the renderer. It decodes every frame
of the MP4, names its mouth shape by the nearest sheet cell, and compares
with `reference.json`: an independent alignment of the audio that went
into the clip, made by Montreal Forced Aligner (the first command;
`lipsync-phonemes` has the one-time install). It counts:

- each P, B, or M with no closed frame (`rest` or `closed`) on screen
  during the phoneme;
- each pause over 150 ms where a frame that lies fully inside the pause is
  not closed, or no frame lies inside it.

The count must be 0. Exit code 0 means pass.

Do not pass the plan's own phones as the reference: the check then only
proves that the plan agrees with itself.

## Results

| Clip | Frames per second | P, B, M | Pauses over 150 ms | Misses |
|---|---|---|---|---|
| 47 s script | 24 | 76 | 17 | 0 |
| 47 s script | 12 | 76 | 17 | 0 |
| 13.2 s demo | 24 | 21 | 7 | 0 |
| 15.6 s demo | 24 | 24 | 7 | 0 |
| 12.6 s demo | 24 | 26 | 3 | 0 |

Before rule 0 existed, a 7.75 s clip missed 3 of 4 pauses. Before `spn` was
treated as speech, one clip missed 1 pause.

## Gotchas

- The reference aligner cannot see a word outside its dictionary. A P, B, or
  M inside such a word is not counted.
- At 12 fps a frame is 83 ms and most phonemes are shorter. Rule 5 keeps the
  closures; other short visemes merge away.
- `rest` and `closed` must really show closed lips in the sheet. Look at the
  cells (`lipsync-sheet`); the check believes the names.

## Tested on, and not

Tested: American English, Kokoro speech, 12 and 24 fps, 12-shape PixelLab
sheets, clips of 8 to 47 s. Not tested: other languages, human recordings,
singing, sheets with fewer than 12 shapes, and frame rates above 24.
