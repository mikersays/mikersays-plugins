---
name: lipsync-clip
description: Render a talking pixel-art character from a mouth sheet, a frame plan, and the narration audio, as an MP4 with ffmpeg or as a static web player that picks its frame from audio.currentTime. Trigger on "render the talking clip", "make the MP4", "web player for the character", "play the lip sync in the browser", or "talking head video from a sprite sheet".
argument-hint: "[sheet.png] [plan.json] [audio.wav]"
allowed-tools: Bash, Read, Write
---

# lipsync-clip: render or play a talking character

This skill does one job: show the frame plan with the audio. Inputs: a
12-cell sheet (`lipsync-sheet`), `plan.json` (`lipsync-plan`), and the WAV
(`lipsync-narrate`).

## Locate the script

```bash
LS="$CLAUDE_PLUGIN_ROOT/scripts"
[ -f "$LS/render_clip.py" ] || LS="$(find ~/.claude/plugins ~/.codex/plugins -type d -path '*/lipsync/scripts' -print -quit 2>/dev/null)"
[ -f "$LS/render_clip.py" ] && echo "scripts: $LS" || echo "lipsync scripts not found"
```

If this prints "lipsync scripts not found", the plugin is not installed
where expected; report that and stop.

The script uses the Python standard library and `ffmpeg` (`brew install
ffmpeg`).

## MP4

```bash
python3 "$LS/render_clip.py" --sheet sheet/neutral.png --plan plan.json --wav narration.wav --out clip.mp4 --scale 4
ffprobe -v error -select_streams v:0 -show_entries stream=nb_frames,r_frame_rate,width,height -of csv=p=0 clip.mp4
```

The file names are examples; give the paths of your own sheet, plan, and
WAV.

- The video has exactly one frame per plan entry at the plan's frame rate,
  so frame `k` covers `k/fps` to `(k+1)/fps` of the audio. Check `nb_frames`
  against the plan.
- `--scale` is a whole number. Pixel art scales by nearest neighbor only;
  4 turns a 128 px cell into 512x512. H.264 needs even sizes, so use an
  even scale when the cell size is odd.
- The encode is H.264 (`-crf 12 -tune animation`, `yuv420p`) with AAC audio.
  A 13 s clip is about 0.25 MB.
- The cell is drawn over the plan's `background` color, because portraits
  have transparent edges.

## Web player

```bash
python3 "$LS/render_clip.py" --sheet sheet/neutral.png --plan plan.json --wav narration.wav --out clip.mp4 --web player
(cd player && python3 -m http.server 4173 >/dev/null 2>&1 &)   # then open http://localhost:4173/
pkill -f "http.server 4173"                                     # stop the server when you are done
```

`--web` needs `--out` too: the command renders the MP4 again and then
writes the player.

`player/` holds `index.html`, `player.js`, `sheet.png`, `audio.wav`, and
`timeline.json`. On every animation frame the page computes
`floor(audio.currentTime * fps)` and draws that cell. It runs no clock of
its own, so the mouth cannot drift, and seeking the audio moves the mouth.
After the audio ends, the page shows the first frame.

- Serve it over HTTP; `fetch` does not work from `file://`.
- All paths are relative, so the folder works under a sub-path such as a
  GitHub Pages project site.
- The audio stays WAV: a compressed format adds encoder delay that the
  page would have to correct.
- `timeline.json` is the whole plan. It includes the text and the phoneme
  list; remove what you do not want public before you publish.

## Verify

1. Run the closed-mouth check of `lipsync-plan` on the MP4. It reads the
   frames back from the file. It needs `reference.json`, an independent
   alignment of the clip's audio: run Montreal Forced Aligner on the same
   WAV that went into the clip (`lipsync-phonemes` has the one-time
   install). Without that tool, skip this step and say so. Do not pass the
   plan's own phones.

   ```bash
   python3 "$LS/align_mfa.py" --wav narration.wav --text-file script.txt --out reference.json --mfa-env ./.mfa
   python3 "$LS/check_closures.py" clip.mp4 --sheet sheet.png --plan plan.json --phones reference.json
   ```
2. For the player, compare the drawn shape with the plan while it plays.
   The page exposes `window.narrator.current()` and
   `window.narrator.shapeAt(t)`. In a headless browser, mute the audio,
   call `audio.play()`, and sample on `requestAnimationFrame` for a few
   seconds. Accept the plan's shape for the current time or for one frame
   earlier, because the page draws once per animation frame:

   ```js
   async () => {
     const a = document.getElementById("audio"); a.muted = true; await a.play();
     let n = 0, bad = 0; const fps = window.narrator.timeline.fps, t0 = performance.now();
     await new Promise(done => { const step = () => {
       const t = a.currentTime, got = window.narrator.current();
       if (got !== window.narrator.shapeAt(t).shape && got !== window.narrator.shapeAt(Math.max(0, t - 1 / fps)).shape) bad++;
       n++; performance.now() - t0 < 4000 ? requestAnimationFrame(step) : done(); };
       requestAnimationFrame(step); });
     a.pause(); return { samples: n, mismatches: bad };
   }
   ```

   Measured: 0 mismatches in 241 samples (4 s) locally and 0 in 301 (5 s)
   on GitHub Pages. Also confirm that no request failed; a missing
   `favicon.ico` is harmless.
3. SyncNet is an optional third measure; see "SyncNet" below.

## SyncNet

SyncNet (`joonson/syncnet_python`, commit 907c0b5, on CPU, no patch needed)
is a second, independent measure of the MP4. Its face detector (S3FD) found
the pixel-art faces: every frame of two human portraits and 281 of 317
frames of a goblin (the tracker filled the rest).

| Clip | Offset | Confidence | Audio shifted +200 ms | Audio shifted -200 ms |
|---|---|---|---|---|
| Woman | +1 frame | 4.23 | -4 frames | +6 frames |
| Bearded man | +1 frame | 4.13 | -4 frames | +6 frames |
| Goblin | +1 frame | 3.94 | -4 frames | +6 frames |

- One frame is 40 ms: the pipeline re-encodes to 25 fps. A positive offset
  means the audio is early relative to the video.
- The controls prove the number means something: a 200 ms shift moved the
  offset by exactly 5 frames each way, and a clip paired with another
  clip's audio scored 0.51 to 1.06.
- The resolution is one frame. With a fixed crop instead of the detector,
  the same clips read -1 frame. Read the result as "within 1 frame", not as
  a 40 ms error to correct.
- The confidence (3.9 to 4.2) is far below the 10.0 of the repository's
  real-face example. Always run the shift controls before you trust an
  offset on drawn faces.

## Gotchas

- The Playwright MCP server writes a snapshot and a console log to
  `.playwright-mcp/` in the session's project folder on every `navigate`,
  and its screenshots may only be written inside that folder. Delete
  `.playwright-mcp/` afterward.
- GitHub Pages answers audio with HTTP 206 (range requests); that is a
  success, not an error.

## Tested on, and not

Tested: 128 px cells at scale 4, 12 and 24 fps, clips of 8 to 47 s, ffmpeg
on macOS, Chromium through Playwright, desktop and a 390 px wide viewport.
Not tested: Safari and Firefox, clips over 60 s, other containers or
codecs, and transparent video.
