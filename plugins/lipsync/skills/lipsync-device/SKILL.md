---
name: lipsync-device
description: Put a talking pixel-art character on a small screen, a 128x64 1-bit OLED (SSD1306 or SH1106) or an M5Stack StickS3, by exporting the frame plan, the audio, and the mouth art as one device pack (.pnpk), playing the pack in a pixel-exact simulator, checking timing and closed mouths on the simulator's MP4, and building the ESP32 example firmware without flashing it. Trigger on "lip sync on an OLED", "talking face on an ESP32", "M5Stack StickS3 narrator", "device pack", "pnpk", "1-bit mouth shapes", or "low-resolution lip sync".
argument-hint: "[plan.json] [audio.wav] [strip.png] [oled|sticks3]"
allowed-tools: Bash, Read, Write
---

# lipsync-device: a spoken line on a small screen

This skill does one job: take one spoken line to a microcontroller's
screen. A microcontroller cannot run the speech model, so the computer does
the work and writes a **device pack** (`.pnpk`). The device only plays the
pack. Inputs: `plan.json` (`lipsync-plan`), the WAV (`lipsync-narrate`), and
an art strip for the panel.

**Warning:** Never flash or upload firmware to a device, and never open a
device's serial port, without asking the user first. A flash replaces
whatever the device runs, and the user may need what it runs now. This
skill ends at a firmware build. Do not add `-t upload` to a `pio` command,
and do not run `pio device monitor`, until the user says yes for that
device.

The skill covers two targets:

| Target | Panel | Pixels in the pack | Sound |
|---|---|---|---|
| `oled` | 128x64, 1 bit per pixel, SH1106 or SSD1306 on I2C | `mono_vpage`: 8-row pages, as the controller stores them | None by default; an I2S amplifier is optional |
| `sticks3` | M5Stack StickS3, 135x240 ST7789, portrait | `rgb565_be`: RGB565, high byte first | ES8311 codec and speaker, through M5Unified |

Other panels work when you describe them (see "Describe another panel").

## Locate the scripts and the device files

```bash
LS="$CLAUDE_PLUGIN_ROOT/scripts"
[ -f "$LS/device_pack.py" ] || LS="$(find ~/.claude/plugins ~/.codex/plugins -type d -path '*/lipsync/scripts' -print -quit 2>/dev/null)"
DEV="$(dirname "$LS")/skills/lipsync-device/assets/device"
[ -f "$LS/device_pack.py" ] && [ -f "$DEV/lib/pnplayer/pn_player.h" ] && echo "scripts: $LS, device: $DEV" || echo "lipsync device files not found"
```

If this prints "lipsync device files not found", the plugin is not
installed where expected; report that and stop.

The following table lists what each step needs:

| Step | Script | Needs |
|---|---|---|
| Export a pack | `device_pack.py` | `uv` (Pillow), `ffmpeg` |
| Simulate | `device_sim.py` | `cc`, `ffmpeg`; standard library only |
| Check a clip | `check_device.py` | `uv` (numpy), `ffmpeg`, `ffprobe` |
| Check 1-bit art | `check_legibility.py` | `uv` (Pillow) |
| Build firmware | `$DEV` (a PlatformIO project) | `pio` |

Every script has a `--selftest`. The file names in the commands below are
examples; give the paths of your own files.

## 1. Make art for the panel

### StickS3 (color)

Use the 12-cell, 128 px sheet of `lipsync-sheet` as it is. The exporter
shows the sheet at 1x, so one art pixel is one panel pixel. The face sits at
(3, 44) over the plan's background color, and `--caption` writes a name
under the face. All 12 shapes are kept. The exporter finds the mouth box:
the smallest box that holds every pixel that differs between two cells. A
sheet in which only the mouth changes gives a small box (48x34 on the test
sheet); a sheet that shimmers gives a large one, and the exporter warns
when the box covers more than half the panel.

### OLED (1 bit)

Draw the face for the 128x64 grid, pixel by pixel. Do not shrink the color
portrait: a 128 px cell scaled to 64 px and thresholded loses the mouth.
Follow these rules:

- **Reduce the viseme set, and state the mapping.** Twelve shapes do not
  stay distinct in a 48x24 box. The preset keeps 7 and maps the 12 plan
  shapes to them. The table below gives the mapping:

  | OLED shape | Plan shapes | Why |
  |---|---|---|
  | `closed` | `rest`, `closed` | One closed mouth serves both |
  | `teeth` | `teeth`, `hiss` | f, v, s, z, sh, ch: teeth together |
  | `small` | `small_open`, `tongue` | The tongue tip is under 2 pixels here |
  | `open` | `medium_open` | k, g, e |
  | `wide` | `wide_open`, `jaw_drop` | The tallest opening does not fit a second size |
  | `smile` | `smile` | ee: wide and flat |
  | `round` | `round_small`, `pucker` | One rounded mouth serves both |

  If you choose another set, write your mapping down in the panel
  description (`shape_map`) and tell the user what merged.
- **Keep closed, open, and rounded apart.** A viewer reads those three
  first. If two shapes must merge, merge inside one of the three groups,
  never across them.
- **Put the mouth box on multiples of 8.** The preset box is x 40, y 40,
  48 wide, 24 high. An SSD1306 or SH1106 updates whole tiles of 8x8 pixels,
  so with this box the device sends only 18 tiles when the mouth changes.
  Only the mouth box may differ between cells.
- **Draw dark mouths on a lit face.** The bare face must light at least
  80% of the mouth box, or a dark mouth has nothing to stand out from. The
  tested faces light 94% to 100%.
- **Meet the legibility rule.** Every two mouth shapes must differ by at
  least 40 pixels inside the mouth box (40 of 1152).

The strip is a horizontal PNG of 7 cells, 128x64 each, in the order
`closed`, `teeth`, `small`, `open`, `wide`, `smile`, `round`. A lit pixel is
white. The skill gives rules, not coordinates: you choose the face. A head
that fills the panel as a close-up, with eyes near y 20 to 30 and the mouth
box left lit, has worked for four faces.

Check the strip by count. The script fails when two mouths differ by fewer
than 40 pixels, when any pixel outside the mouth box changes between
cells, or when the most lit cell lights less than 80% of the mouth box:

```bash
uv run "$LS/check_legibility.py" --strip wren=oled/wren.png
```

The check prints the pairwise matrix and `LEGIBILITY PASS` or
`LEGIBILITY FAIL`. On the three tested characters the closest pair was
`closed` / `small` at 67 pixels.

The count cannot tell whether a shape reads as the right mouth. For that,
run a blind-reader trial:

```bash
uv run "$LS/check_legibility.py" --strip wren=oled/wren.png --trials trials/ --key key.json
uv run "$LS/check_legibility.py" --strip wren=oled/wren.png --key key.json --score answers.json
```

The first command writes each cell as `trials/trial-NN.png` in a shuffled
order. Give the trial files and the list of shape names, but not the key and
not the strip, to a reader who has never seen the art (a fresh subagent
works). The reader writes `answers.json`, which maps each trial name to the
shape named. The second command prints the confusion matrix. Shapes that the
reader confuses across the closed, open, and rounded groups need a redraw.
On the tested art a blind reader named 21 of 21 frames correctly.

## 2. Export a pack

```bash
uv run "$LS/device_pack.py" --plan plan.json --wav narration.wav --strip oled/wren.png \
    --target oled --out line.oled.pnpk
uv run "$LS/device_pack.py" --plan plan.json --wav narration.wav --strip sheet/neutral.png \
    --target sticks3 --caption WREN --out line.sticks3.pnpk
```

Each command writes the pack and `<pack>.json` (the frame names, the closed
frames, the runs, and the sizes). The simulator and the checks read the
JSON; the device does not.

- `--plan` takes the plan file of `lipsync-plan`. A pixel-narrator
  `.timeline.json` has the same fields and works unchanged.
- The exporter resamples the audio to 16 kHz mono (`--rate`) and stores it
  as IMA ADPCM (`--audio adpcm`; `pcm16` and `none` exist).
- The frame plan becomes runs: a frame index and a duration in audio
  samples. The plan has one shape per 1/fps second, so a pause can begin up
  to one plan frame before the mouth closes, and a 60 Hz panel would show
  that. The exporter therefore cuts each of the plan's `silences` into the
  runs at sample accuracy. A shape that the cut leaves shorter than 1/30 s
  joins its neighbor.
- A pack holds at most 16 mouth frames. Shapes with identical pixels share
  one frame.

### The pack format

One pack is one spoken line. `$DEV/lib/pnplayer/pn_player.h` is the
authority for the byte layout. All integers are little-endian:

| Offset | Size | Field |
|---|---|---|
| 0 | 4 | Magic `PNPK` |
| 4 | 1 | Version (1) |
| 5 | 1 | Pixel format: 1 = `mono_vpage`, 2 = `rgb565_be` |
| 6 | 1 | Audio format: 0 = none, 1 = PCM16, 2 = IMA ADPCM |
| 7 | 1 | Frame count (1 to 16) |
| 8 | 2+2 | Panel width, height |
| 12 | 2x4 | Base image rectangle: x, y, width, height |
| 20 | 2x4 | Mouth rectangle: x, y, width, height |
| 28 | 4 | Audio sample rate in Hz |
| 32 | 4 | Audio sample count |
| 36 | 4 | Run count |
| 40 | 2 | ADPCM block size in bytes (0 for other formats) |
| 42 | 2 | Closed mask: bit i is set when frame i is a closed mouth |
| 44, 48, 52, 56 | 4 each | Offsets of the base image, the frames, the runs, the audio |
| 60 | 4 | Audio size in bytes |

After the 64-byte header come the base image (the whole panel with the
mouth closed), the mouth frames, the runs (4 bytes each: frame index, then
the duration in samples as 3 bytes), and the audio. `mono_vpage` stores one
byte per column per 8 rows, top pixel in bit 0. An ADPCM block of 256 bytes
holds 505 samples and decodes on its own.

### Sizes

Speech costs about 8.1 KB per second at 16 kHz ADPCM (8,111 bytes). A 13 s
line is about 110 KB for the OLED (109,528 bytes: base 1,024, 7 frames
1,008, runs 424, audio 107,008) and about 205 KB for the StickS3 (204,940
bytes: base 64,800, 10 frames 32,640, runs 428, audio 107,008).

### Describe another panel

`device_pack.py --print-preset oled` prints a preset as JSON. Edit a copy
and pass it with `--panel-file`, or override single values (`--panel WxH`,
`--pixel-format`, `--cell`, `--cell-xy`, `--shapes`, `--shape-map`,
`--closed`, `--base-shape`, `--mouth-box X,Y,W,H|auto`, `--background`).
The script's docstring lists every key. The C player handles any panel size
in the two pixel formats; the example firmware handles only the two
targets.

## 3. Play the pack in the simulator

```bash
python3 "$LS/device_sim.py" line.oled.pnpk --out line.oled.mp4
python3 "$LS/device_sim.py" line.sticks3.pnpk --out line.sticks3.mp4
python3 "$LS/device_sim.py" line.oled.pnpk --out line.oled-clock.mp4 --speaker none
```

The simulator is the firmware's own `pn_player.c`, compiled for this
computer with `cc` and driven through the same HAL. Its panel is a block of
display memory in the panel's format, recorded 60 times per second. The MP4
shows one panel pixel as a block of 4x4 (1 bit) or 2x2 (RGB565) video
pixels. Next to the MP4 the wrapper writes `<name>.events.csv` (every draw
and its time) and `<name>.sim.json`.

`--speaker` picks the audio output to imitate: `i2s` (the default for a
1-bit pack), `m5` (M5Unified's speaker, the default for RGB565), or `none`.
The OLED example firmware has no speaker by default, so also simulate the
OLED pack with `--speaker none`: the player then follows the timer.

Look at the MP4 before you go on.

## 4. Run the checks

```bash
uv run "$LS/check_device.py" line.oled.mp4 --phones reference.json --out line.oled.check.json
```

The check reads the MP4, not the plan as drawn. It takes one pixel from the
center of each enlarged panel pixel, which gives the framebuffer back at 1x,
and matches each framebuffer to the pack's frames. It runs three checks:

- **Framebuffer.** No framebuffer may differ from its pack frame. Pass: 0.
- **Timing.** The video must show exactly the pack's frame changes, in
  order, each within one panel frame (16.667 ms at 60 fps) of the start of
  its run. Errors up to 16.646 ms are normal: a change that is due just
  after a panel frame starts shows on the next one.
- **Closed mouth** (only with `--phones`). Every P, B, and M has a closed
  frame on screen, and every pause over 150 ms shows only closed frames.
  Pass: 0 misses.

`reference.json` must be an independent alignment of the clip's sound, not
the plan's own phones. Make it with Montreal Forced Aligner
(`lipsync-phonemes` has the one-time install):

```bash
ffmpeg -v error -y -i line.oled.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le line.oled.audio.wav
python3 "$LS/align_mfa.py" --wav line.oled.audio.wav --text-file script.txt --out reference.json --mfa-env ./.mfa
```

A clip made with `--speaker none` has no sound; pass the reference of the
same line's clip with sound. Without the aligner, leave `--phones` out. The
check then prints `DEVICE CHECK CLOSURES SKIPPED`; tell the user that the
closed-mouth check did not run.

Exit code 0 means that every check that ran passed. Measured on the 13 s
test line: 0 of 791 framebuffers differ, 106 changes for 106 planned (OLED)
and 107 for 107 (StickS3), largest timing error 10.0 ms, and 0 misses on 21
P, B, M and 7 pauses.

## 5. Build the firmware, then stop

`$DEV` is one PlatformIO project: the C player (`lib/pnplayer/`), example
firmware for both boards (`src/sticks3/`, `src/oled/`), the simulator
source (`sim/`), and 13 unit tests of the player (`test/test_player/`).
Build a copy, not the plugin's folder:

1. Copy the project to a work folder: `cp -R "$DEV" firmware`.
2. Copy your packs under the names the firmware embeds:
   `cp line.oled.pnpk firmware/packs/demo.oled.pnpk` and
   `cp line.sticks3.pnpk firmware/packs/demo.sticks3.pnpk`.
3. Run the unit tests on this computer: `(cd firmware && pio test -e native)`.
   All 13 must pass.
4. Build: `(cd firmware && pio run -e sticks3 -e oled)`. The first build
   downloads the toolchain and the libraries. Run one build at a time.
5. Report the flash and RAM figures that `pio` prints, and stop.

Do not flash. Ask the user first, name the device and its port, and wait
for a yes (see the warning at the top).

The following table lists the environments and their measured sizes with
the 13 s test line embedded:

| Environment | Board | Flash | RAM |
|---|---|---|---|
| `sticks3` | StickS3 | 732,649 of 3,342,336 bytes (21.9%) | 24,712 of 327,680 bytes (7.5%) |
| `oled` | ESP32 DevKit, SH1106, no speaker | 397,273 of 1,310,720 bytes (30.3%) | 23,688 of 327,680 bytes (7.2%) |
| `oled_ssd1306` | ESP32 DevKit, SSD1306, no speaker | 397,273 bytes | 23,688 bytes |
| `oled_i2s` | ESP32 DevKit, SH1106, MAX98357A amplifier | 412,945 bytes | 23,712 bytes |

### Hardware facts

StickS3:

- The module is an ESP32-S3-PICO-1-N8R8: 8 MB flash and 8 MB octal PSRAM.
  The project uses `board = esp32-s3-devkitc-1`, `default_8MB.csv`, and
  `memory_type = qio_opi`.
- The panel is a 135x240 ST7789. M5Unified drives it in RGB565; rotation 0
  is portrait. The pack's bytes go to `pushImage` as `lgfx::swap565_t`
  with no conversion.
- An ES8311 codec drives the speaker; the example plays sound with
  `M5.Speaker.playRaw`. Keep the volume at or below about 180 of 255 on battery: louder can reset
  the board. The example uses 150.
- `M5.Speaker` keeps a pointer to the samples, not a copy, so the example
  rotates three buffers.

OLED:

- The controller is an SH1106 or an SSD1306 on I2C: SDA 21, SCL 22,
  address 0x3C, through U8g2 at 400 kHz.
- SH1106 and SSD1306 are not interchangeable in the driver: the wrong one
  shows a shifted or garbled picture. Both take the same pack. The default
  environment `oled` is SH1106; `oled_ssd1306` is the SSD1306 build. Ask
  the user which controller the board carries.
- `oled_i2s` adds a MAX98357A amplifier on BCLK 26, LRC 25, DIN 27. Without
  it the board has no speaker and the frame follows the timer.
- With the default partitions of a 4 MB ESP32 DevKit, the app partition is
  1,310,720 bytes: room for about 2 minutes of speech in one pack.

### How the player keeps time

The player (C99, no operating-system calls, no heap) picks the frame from
the audio position, not from a timer:

1. The player hands the speaker 256 samples at a time and counts what the
   speaker accepts.
2. When the speaker accepts a chunk after it was full, exactly
   `latency_samples` samples are still unplayed. That fixes the position.
3. Between two such moments the timer fills in, but never past the samples
   that were handed over.

So a timer error cannot build up, and a stalled audio feed stalls the
mouth. With no speaker (`audio_write` is NULL), the position follows the
timer alone. A board supplies the HAL in `pn_player.h`: a microsecond
clock, a non-blocking audio write, two draw calls, `latency_samples`, and
`draw_lead_us`.

The constants `draw_lead_us` (2700 for the StickS3, 4000 for the OLED) and
`latency_samples` in the example firmware are estimates. Nobody has
measured them on hardware, because the example firmware has been built but
has never run on a device. The simulator's speaker is ideal, with no codec
delay and no jitter. A passing check therefore proves the player's logic
and the pack, not the audio latency of a real board. Say so when you
report.

## Gotchas

- The caption uses Pillow's default font, so its pixels can change with the
  Pillow version. The mouth frames do not depend on it.
- `tools/make_fixture.py` in the project writes the unit tests' fixture
  packs with `device_pack.py`, so the tests hold the exporter and the
  player to one byte layout. In a copy outside the plugin, pass
  `--exporter "$LS/device_pack.py"`.
- `packs/` ships empty. A build without `packs/demo.<target>.pnpk` fails
  at the embed step.
- A build leaves `.pio/` in the work folder (hundreds of megabytes). Delete
  the folder when the user no longer needs the build.

## Tested on, and not

Tested: three 1-bit faces and three 128 px sheets, lines of 12.6 to 15.6 s
at 24 fps, both presets, the simulator on macOS (Apple Silicon), PlatformIO
builds of all four environments, and the 13 native unit tests. Not tested:
any real device (nothing was flashed), panels other than the two presets,
lines over 16 s, `pcm16` packs in the firmware, and Linux or Windows hosts.
