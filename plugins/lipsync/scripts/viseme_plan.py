#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Turn timed phonemes into one mouth-shape name per video frame (a plan file).

Stdlib only. Inputs: a phones file (`{"text", "duration", "source", "phones":
[[start, end, label], ...]}`; labels are ARPAbet with an optional stress digit,
`sil` for silence, `spn` for an unknown spoken word) and, optionally, the WAV
of the audio (16-bit PCM, mono or stereo). Output: a plan file with `fps`,
`duration`, `shapes` (the 12 shape names in sheet order), `closed_shapes`,
`frames` (one shape name per video frame), `runs`, `text`, `phones`,
`silences`, `timing_source`, `cell` and `background`.

The pipeline is ARPAbet phoneme -> Oculus viseme -> mouth shape (`--table`
prints it). The rules, in the order they run:

0. Where the audio is silent for 100 ms or more, the phonemes give way to
   silence. This uses the measured sound, not the phoneme times.
1. A pause shorter than `min_pause` does not close the mouth. Its time goes
   to the phonemes on each side.
2. A diphthong becomes two visemes. HH takes the shape of the next phoneme,
   because the mouth already forms the vowel while the breath sounds. A
   schwa opens the mouth half way, and an open vowel with primary stress
   takes the widest shape.
3. A viseme shorter than one frame merges into its longer neighbor. Lip
   closures (/p b m/) and pauses are exempt.
4. Each frame shows the shape that covers most of it.
5. Every /p b m/ gets at least one closed frame, and every pause of
   `min_pause` or longer shows the rest shape on all frames inside it. These
   two rules win over rule 4.

Usage:
    uv run viseme_plan.py --phones phones.json --wav audio.wav --fps 24 --out plan.json
    uv run viseme_plan.py --table
    uv run viseme_plan.py --selftest

Options: `--cell 128` (sheet cell size in pixels), `--background "#1e1e2e"`,
`--shape-map overrides.json` (a JSON object that maps an Oculus viseme name,
or `aa_stressed`, to a shape name), `--no-audio-silence` (skip the WAV
silence detection and use only the phoneme times).
Exit code 0 on success; non-zero with a one-line reason on failure.
"""

from __future__ import annotations

import argparse
import array
import json
import math
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Phoneme-to-viseme tables
#
# Published table: OCULUS is the 15-viseme set of the Oculus Lipsync SDK, from
# the "Viseme Reference" page of the Meta developer documentation (read on
# 2026-11-22):
# https://developers.meta.com/horizon/documentation/unity/audio-ovrlipsync-viseme-reference/
#
# The page lists each viseme with its phonemes and example words:
#
#     sil  neutral            PP  p, b, m (put, bat, mat)   FF  f, v (fat, vat)
#     TH   th (think, that)   DD  t, d (tip, doll)          kk  k, g (call, gas)
#     CH   tS, dZ, S (chair, join, she)                     SS  s, z (sir, zeal)
#     nn   n, l (lot, not)    RR  r (red)                   aa  A: (car)
#     E    e (bed)            I   ih (tip)                  O   oh (toe)
#     U    ou (book)
#
# For how the 15 were chosen, the page points to the MPEG-4 facial animation
# overview. Meta marks the page as no longer updated.
#
# ARPABET_TO_OCULUS marks every row as "published" (the page lists the
# phoneme or uses it in an example word) or "extended" (the page has no row
# for the phoneme, so this project assigns the viseme with the nearest lip
# and jaw position). The extensions are this project's choice.
#
# Mouth shapes: SHAPES are the 12 mouth positions that PixelLab
# `create_vocal_animation` draws with `viseme_count=12`. OCULUS_TO_SHAPE picks
# one shape per viseme. A character can override single rows (--shape-map)
# when its sprite sheet lacks a usable frame for a shape.
# ---------------------------------------------------------------------------

# The 15 Oculus visemes, in the SDK's order.
OCULUS = [
    "sil", "PP", "FF", "TH", "DD", "kk", "CH", "SS",
    "nn", "RR", "aa", "E", "I", "O", "U",
]

# ARPAbet phoneme -> (list of Oculus visemes, provenance).
# A diphthong maps to two visemes: the mouth moves during the vowel.
ARPABET_TO_OCULUS: dict[str, tuple[list[str], str]] = {
    # Consonants on the reference page.
    "P": (["PP"], "published"),
    "B": (["PP"], "published"),
    "M": (["PP"], "published"),
    "F": (["FF"], "published"),
    "V": (["FF"], "published"),
    "TH": (["TH"], "published"),
    "DH": (["TH"], "published"),  # "that"
    "T": (["DD"], "published"),
    "D": (["DD"], "published"),
    "K": (["kk"], "published"),
    "G": (["kk"], "published"),
    "CH": (["CH"], "published"),
    "JH": (["CH"], "published"),
    "SH": (["CH"], "published"),
    "S": (["SS"], "published"),
    "Z": (["SS"], "published"),
    "N": (["nn"], "published"),
    "L": (["nn"], "published"),
    "R": (["RR"], "published"),
    # Vowels on the reference page.
    "AA": (["aa"], "published"),
    "EH": (["E"], "published"),
    "IH": (["I"], "published"),
    "OW": (["O", "U"], "published"),  # "toe"; the glide closes toward U
    "UH": (["U"], "published"),       # "book"
    # Extensions: the page gives no row for these phonemes.
    "ZH": (["CH"], "extended"),   # voiced partner of SH
    "NG": (["kk"], "extended"),   # velar, like K and G
    "HH": (["kk"], "extended"),   # open glottal; replaced by the next vowel
    "W": (["U"], "extended"),     # tightly rounded lips
    "Y": (["I"], "extended"),     # spread lips, like IY
    "ER": (["RR"], "extended"),   # r-colored vowel
    "AE": (["aa"], "extended"),   # open front vowel
    "AH": (["aa"], "extended"),   # open central vowel and schwa
    "AO": (["O"], "extended"),    # open rounded vowel
    "IY": (["I"], "extended"),    # spread vowel
    "UW": (["U"], "extended"),    # rounded vowel, as in "boot"
    "EY": (["E", "I"], "extended"),
    "AY": (["aa", "I"], "extended"),
    "AW": (["aa", "U"], "extended"),
    "OY": (["O", "I"], "extended"),
}

# Phonemes that close the lips. The mouth must show a closed frame on each.
BILABIALS = {"P", "B", "M"}

# Labels that mean "no speech" in aligner and model output.
SILENCE_LABELS = {"", "sil", "sp", "<eps>", "SIL", "pau"}

# Montreal Forced Aligner labels a word that its dictionary lacks as "spn"
# (spoken noise). It is speech, not silence, with unknown phonemes.
UNKNOWN_SPEECH = {"spn"}

# The 12 PixelLab mouth positions, by the names the service reports.
SHAPES = [
    "rest", "closed", "small_open", "medium_open", "wide_open", "smile",
    "round_small", "pucker", "teeth", "hiss", "tongue", "jaw_drop",
]

# Shapes with the lips together. The closure check counts only these as closed.
CLOSED_SHAPES = {"rest", "closed"}

# Oculus viseme -> mouth shape.
OCULUS_TO_SHAPE: dict[str, str] = {
    "sil": "rest",          # silence: lips together, relaxed
    "PP": "closed",         # p, b, m: lips pressed
    "FF": "teeth",          # f, v: upper teeth on the lower lip
    "TH": "tongue",         # th: tongue tip between the teeth
    "DD": "small_open",     # t, d: tongue behind the teeth, jaw nearly shut
    "kk": "medium_open",    # k, g: back of the tongue, jaw part open
    "CH": "hiss",           # ch, j, sh: teeth together, lips pushed out
    "SS": "hiss",           # s, z: teeth together
    "nn": "small_open",     # n, l: tongue up, jaw nearly shut
    "RR": "round_small",    # r: lips slightly rounded
    "aa": "wide_open",      # open vowels
    "E": "medium_open",     # e as in "bed"
    "I": "smile",           # i as in "tip", ee: lips spread
    "O": "round_small",     # o as in "toe": rounded
    "U": "pucker",          # oo, w: tight round lips
}


def strip_stress(phone: str) -> str:
    """Return an ARPAbet phoneme without its stress digit: "AH0" -> "AH"."""
    return phone.rstrip("012").upper()


def is_silence(label: str) -> bool:
    return label.strip() in SILENCE_LABELS


def oculus_for(phone: str) -> list[str]:
    """Return the Oculus visemes for one ARPAbet phoneme or silence label."""
    if is_silence(phone):
        return ["sil"]
    if phone in UNKNOWN_SPEECH:
        return ["E"]  # a half-open mouth: the sound is speech of unknown shape
    base = strip_stress(phone)
    if base not in ARPABET_TO_OCULUS:
        raise KeyError(f"no viseme for phoneme {phone!r}")
    return ARPABET_TO_OCULUS[base][0]


def table_text() -> str:
    """Return the ARPAbet -> Oculus viseme -> shape table as text."""
    lines = [f"{'ARPAbet':8s} {'Oculus':8s} {'shape':32s} source"]
    for arpa, (visemes, source) in ARPABET_TO_OCULUS.items():
        shapes = "+".join(OCULUS_TO_SHAPE[v] for v in visemes)
        lines.append(f"{arpa:8s} {'+'.join(visemes):8s} {shapes:32s} {source}")
    lines.append(f"{'spn':8s} {'E':8s} {OCULUS_TO_SHAPE['E']:32s} unknown spoken word")
    lines.append(f"{'sil':8s} {'sil':8s} {OCULUS_TO_SHAPE['sil']:32s} silence")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Timeline: timed phonemes -> one shape per frame
#
# Check 3 requires closed frames on pauses over 150 ms; MIN_PAUSE of 100 ms
# leaves a margin for timing error.
# ---------------------------------------------------------------------------

# A pause at least this long closes the mouth.
MIN_PAUSE = 0.10

# Open vowels that take the jaw-drop shape under primary stress.
STRESSED_WIDE = {"AA", "AE", "AW", "AY"}

# Share of a diphthong's time that its first viseme gets.
DIPHTHONG_SPLIT = 0.55


@dataclass
class Phone:
    start: float
    end: float
    label: str  # ARPAbet, with or without a stress digit, or a silence label

    @property
    def dur(self) -> float:
        return self.end - self.start


@dataclass
class Segment:
    start: float
    end: float
    shape: str
    protected: bool = False  # a lip closure or a real pause; never merged away

    @property
    def dur(self) -> float:
        return self.end - self.start


def normalize(phones: list[Phone], duration: float) -> list[Phone]:
    """Return phones that cover [0, duration] with no gaps or overlaps.

    Gaps become silence, and neighboring silences join into one.
    """
    out: list[Phone] = []
    t = 0.0
    for p in sorted(phones, key=lambda p: p.start):
        start = max(p.start, t)
        end = min(p.end, duration)
        if end <= start:
            continue
        if start > t + 1e-6:
            out.append(Phone(t, start, "sil"))
        out.append(Phone(start, end, "sil" if is_silence(p.label) else p.label))
        t = end
    if t < duration - 1e-6:
        out.append(Phone(t, duration, "sil"))
    joined: list[Phone] = []
    for p in out:
        if joined and is_silence(p.label) and is_silence(joined[-1].label):
            joined[-1].end = p.end
        else:
            joined.append(p)
    return joined


def apply_silence(phones: list[Phone], silences: list[tuple[float, float]]) -> list[Phone]:
    """Turn the part of every phone that lies in measured silence into silence.

    A TTS duration model stretches the last phoneme of a phrase across the
    pause that follows it. The audio decides: where it is silent, the mouth
    is at rest, whatever the phoneme times say.
    """
    out: list[Phone] = []
    for p in phones:
        pieces = [(p.start, p.end)]
        if not is_silence(p.label):
            for s0, s1 in silences:
                nxt = []
                for a, b in pieces:
                    if s1 <= a or s0 >= b:
                        nxt.append((a, b))
                        continue
                    if a < s0:
                        nxt.append((a, s0))
                    if s1 < b:
                        nxt.append((s1, b))
                pieces = nxt
        out += [Phone(a, b, p.label) for a, b in pieces if b - a > 1e-6]
    out += [Phone(s0, s1, "sil") for s0, s1 in silences]
    return sorted(out, key=lambda p: (p.start, p.end))


def absorb_short_pauses(phones: list[Phone], min_pause: float) -> list[Phone]:
    """Give each pause shorter than `min_pause` to the phonemes around it."""
    out: list[Phone] = []
    n = len(phones)
    for i, p in enumerate(phones):
        short = is_silence(p.label) and p.dur < min_pause
        if not short or i == 0 or i == n - 1:
            out.append(Phone(p.start, p.end, p.label))
            continue
        mid = (p.start + p.end) / 2
        out[-1].end = mid
        # The next phone starts at the midpoint; record that for the loop.
        phones[i + 1] = Phone(mid, phones[i + 1].end, phones[i + 1].label)
    return out


def to_segments(phones: list[Phone], shape_map: dict[str, str]) -> list[Segment]:
    """Expand phones into mouth-shape segments (rule 2)."""
    segs: list[Segment] = []
    for i, p in enumerate(phones):
        if is_silence(p.label):
            segs.append(Segment(p.start, p.end, shape_map["sil"], protected=True))
            continue
        base = strip_stress(p.label)
        visemes = oculus_for(p.label)
        if base == "HH":
            nxt = next(
                (q for q in phones[i + 1:i + 2] if not is_silence(q.label)), None
            )
            if nxt is not None and strip_stress(nxt.label) != "HH":
                visemes = oculus_for(nxt.label)[:1]
        protected = base in BILABIALS
        shapes = [shape_map[v] for v in visemes]
        # Two refinements inside the "aa" viseme, which covers every open
        # vowel. A schwa (unstressed AH) opens the jaw only part way, and a
        # vowel with primary stress opens it furthest.
        if visemes[0] == "aa":
            if base == "AH" and p.label.endswith("0"):
                shapes[0] = shape_map["E"]
            elif p.label.endswith("1") and base in STRESSED_WIDE:
                shapes[0] = shape_map.get("aa_stressed", "jaw_drop")
        if len(shapes) == 1:
            segs.append(Segment(p.start, p.end, shapes[0], protected))
        else:
            cut = p.start + p.dur * DIPHTHONG_SPLIT
            segs.append(Segment(p.start, cut, shapes[0]))
            segs.append(Segment(cut, p.end, shapes[1]))
    return join_equal(segs)


def join_equal(segs: list[Segment]) -> list[Segment]:
    """Join neighbors that show the same shape."""
    out: list[Segment] = []
    for s in segs:
        if out and out[-1].shape == s.shape and out[-1].protected == s.protected:
            out[-1].end = s.end
        else:
            out.append(Segment(s.start, s.end, s.shape, s.protected))
    return out


def merge_short(segs: list[Segment], frame: float) -> list[Segment]:
    """Merge each unprotected segment shorter than one frame (rule 3).

    The shortest segment goes first. It joins its longer unprotected
    neighbor; if both neighbors are protected, they share its time.
    """
    segs = [Segment(s.start, s.end, s.shape, s.protected) for s in segs]
    while True:
        short = [
            i for i, s in enumerate(segs)
            if not s.protected and s.dur < frame - 1e-9 and len(segs) > 1
        ]
        if not short:
            return join_equal(segs)
        i = min(short, key=lambda k: segs[k].dur)
        s = segs[i]
        left = segs[i - 1] if i > 0 else None
        right = segs[i + 1] if i + 1 < len(segs) else None
        free = [n for n in (left, right) if n is not None and not n.protected]
        if free:
            target = max(free, key=lambda n: n.dur)
            if target is left:
                left.end = s.end
            else:
                right.start = s.start
        elif left is not None and right is not None:
            mid = (s.start + s.end) / 2
            left.end = mid
            right.start = mid
        elif left is not None:
            left.end = s.end
        else:
            right.start = s.start
        del segs[i]
        segs = join_equal(segs)


def sample_frames(segs: list[Segment], n_frames: int, fps: float) -> list[str]:
    """Pick the shape that covers most of each frame (rule 4)."""
    frames: list[str] = []
    j = 0
    for k in range(n_frames):
        f0, f1 = k / fps, (k + 1) / fps
        while j < len(segs) - 1 and segs[j].end <= f0:
            j += 1
        cover: dict[str, float] = {}
        m = j
        while m < len(segs) and segs[m].start < f1:
            overlap = min(f1, segs[m].end) - max(f0, segs[m].start)
            if overlap > 0:
                cover[segs[m].shape] = cover.get(segs[m].shape, 0.0) + overlap
            m += 1
        frames.append(max(cover, key=cover.get) if cover else segs[-1].shape)
    return frames


def frames_overlapping(start: float, end: float, n_frames: int, fps: float) -> range:
    """Return the indexes of the frames that share time with [start, end)."""
    first = max(0, int(math.floor(start * fps + 1e-9)))
    last = min(n_frames - 1, int(math.ceil(end * fps - 1e-9)) - 1)
    return range(first, max(first, last) + 1)


def enforce_closures(
    frames: list[str],
    phones: list[Phone],
    fps: float,
    shape_map: dict[str, str],
    min_pause: float,
) -> list[str]:
    """Apply rule 5: closed frames on /p b m/ and on pauses."""
    frames = list(frames)
    n = len(frames)
    for p in phones:
        if is_silence(p.label):
            if p.dur < min_pause:
                continue
            inside = [
                k for k in frames_overlapping(p.start, p.end, n, fps)
                if p.start <= (k + 0.5) / fps < p.end
            ]
            if not inside:
                inside = [min(n - 1, int((p.start + p.end) / 2 * fps))]
            for k in inside:
                frames[k] = shape_map["sil"]
        elif strip_stress(p.label) in BILABIALS:
            hit = frames_overlapping(p.start, p.end, n, fps)
            if not any(frames[k] in CLOSED_SHAPES for k in hit):
                frames[min(n - 1, int((p.start + p.end) / 2 * fps))] = shape_map["PP"]
    return frames


def build_frames(
    phones: list[Phone],
    duration: float,
    fps: float = 24,
    shape_map: dict[str, str] | None = None,
    min_pause: float = MIN_PAUSE,
    silences: list[tuple[float, float]] | None = None,
) -> list[str]:
    """Return one mouth-shape name per video frame for the whole clip.

    `silences` are the silent stretches measured on the audio
    (`silence_runs`); they override the phoneme times.
    """
    shape_map = {**OCULUS_TO_SHAPE, **(shape_map or {})}
    n_frames = max(1, math.ceil(duration * fps - 1e-9))
    if silences:
        phones = apply_silence(phones, silences)
    phones = normalize(phones, duration)
    spoken = absorb_short_pauses([Phone(p.start, p.end, p.label) for p in phones], min_pause)
    segs = merge_short(to_segments(spoken, shape_map), 1.0 / fps)
    frames = sample_frames(segs, n_frames, fps)
    return enforce_closures(frames, spoken, fps, shape_map, min_pause)


def runs(frames: list[str], fps: float) -> list[dict]:
    """Compress the frame list into runs: [{"t": start seconds, "frame": k, "shape": name}]."""
    out: list[dict] = []
    for k, shape in enumerate(frames):
        if not out or out[-1]["shape"] != shape:
            out.append({"t": round(k / fps, 6), "frame": k, "shape": shape})
    return out


# ---------------------------------------------------------------------------
# Silence detection on a 16-bit PCM WAV, stdlib only
# ---------------------------------------------------------------------------

# A stretch of audio counts as silence when its level stays this far below
# the clip's loudest 10 ms for at least MIN_SILENCE seconds.
SILENCE_DB = -35.0
MIN_SILENCE = 0.10


def read_wav_mono(path: Path) -> tuple[list[float], int]:
    """Read a 16-bit PCM WAV and return (mono samples as floats, sample rate).

    A stereo file is averaged to mono. Raise ValueError for other formats.
    """
    with wave.open(str(path), "rb") as w:
        channels, width, rate, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if width != 2:
        raise ValueError(f"{path}: need 16-bit PCM WAV, got {8 * width}-bit")
    data = array.array("h")
    data.frombytes(raw)
    if sys.byteorder == "big":
        data.byteswap()
    if channels == 1:
        return [float(v) for v in data], rate
    return [sum(data[i:i + channels]) / channels for i in range(0, len(data) - channels + 1, channels)], rate


def silence_runs(
    audio: list[float],
    sample_rate: int,
    threshold_db: float = SILENCE_DB,
    min_len: float = MIN_SILENCE,
) -> list[tuple[float, float]]:
    """Return the (start, end) times of the silent stretches in `audio`.

    The level is the RMS of 10 ms windows, 5 ms apart, relative to the
    loudest window. On a 47 s test script these stretches contain every pause
    that Montreal Forced Aligner finds: they start 15 to 60 ms before the
    aligner's pause and end 5 to 45 ms after it.
    """
    hop = int(sample_rate * 0.005)
    win = 2 * hop
    if hop < 1 or len(audio) < win:
        return []
    # Running sum of squares: the energy of any window is two lookups.
    cum = [0.0]
    acc = 0.0
    for v in audio:
        acc += v * v
        cum.append(acc)
    rms = [
        math.sqrt(max(cum[i + win] - cum[i], 0.0) / win)
        for i in range(0, len(audio) - win + 1, hop)
    ]
    top = max(max(rms), 1e-9 * 32768)  # sample scale is the 16-bit integer range
    quiet = [20 * math.log10(r / top + 1e-9) < threshold_db for r in rms]
    found: list[tuple[float, float]] = []
    start = None
    for i, q in enumerate(quiet):
        if q and start is None:
            start = i
        elif not q and start is not None:
            found.append((start * hop / sample_rate, (i * hop + hop) / sample_rate))
            start = None
    if start is not None:
        found.append((start * hop / sample_rate, len(audio) / sample_rate))
    return [(s, e) for s, e in found if e - s >= min_len]


# ---------------------------------------------------------------------------
# Plan file
# ---------------------------------------------------------------------------

def load_phones(path: Path) -> dict:
    doc = json.loads(path.read_text())
    if not isinstance(doc, dict) or "phones" not in doc:
        raise ValueError(f"{path}: not a phones file (no 'phones' list)")
    return doc


def make_plan(
    doc: dict,
    fps: int,
    duration: float,
    silences: list[tuple[float, float]],
    shape_map: dict[str, str] | None = None,
    cell: int = 128,
    background: str = "#1e1e2e",
) -> dict:
    """Build the plan file's content from a phones file's content."""
    phones = [Phone(float(s), float(e), str(label)) for s, e, label in doc["phones"]]
    frames = build_frames(phones, duration, fps, shape_map, silences=silences)
    return {
        "fps": fps,
        "duration": round(duration, 6),
        "cell": cell,
        "shapes": SHAPES,
        "closed_shapes": sorted(CLOSED_SHAPES),
        "background": background,
        "timing_source": doc.get("source", ""),
        "text": doc.get("text", ""),
        "runs": runs(frames, fps),
        "frames": frames,
        "phones": [[round(p.start, 4), round(p.end, 4), p.label] for p in phones],
        "silences": [[round(s, 4), round(e, 4)] for s, e in silences],
    }


def check_shape_map(m: object) -> dict[str, str]:
    if not isinstance(m, dict):
        raise ValueError("shape map must be a JSON object")
    for key, shape in m.items():
        if key != "aa_stressed" and key not in OCULUS:
            raise ValueError(f"shape map: unknown viseme {key!r}")
        if shape not in SHAPES:
            raise ValueError(f"shape map: unknown shape {shape!r}")
    return m


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def _write_wav(path: Path, parts: list[tuple[float, float]], rate: int = 16000, channels: int = 1) -> None:
    """Write tone/silence parts [(seconds, amplitude 0..1), ...] as 16-bit PCM."""
    samples = array.array("h")
    n0 = 0
    for secs, amp in parts:
        n = int(secs * rate)
        for i in range(n):
            v = int(amp * 20000 * math.sin(2 * math.pi * 220 * (n0 + i) / rate))
            samples.extend([v] * channels)
        n0 += n
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples.tobytes())


def selftest() -> None:
    # Silence detector: tone, 0.30 s of near-silence, tone. A stereo copy too.
    with tempfile.TemporaryDirectory() as tmp:
        for ch in (1, 2):
            wav = Path(tmp) / f"tone{ch}.wav"
            _write_wav(wav, [(0.5, 1.0), (0.3, 0.0001), (0.5, 1.0)], channels=ch)
            audio, rate = read_wav_mono(wav)
            found = silence_runs(audio, rate)
            assert len(found) == 1, found
            s, e = found[0]
            assert abs(s - 0.5) < 0.02 and abs(e - 0.8) < 0.02, found
        # A silence shorter than 0.10 s is not reported.
        wav = Path(tmp) / "short.wav"
        _write_wav(wav, [(0.5, 1.0), (0.05, 0.0001), (0.5, 1.0)])
        audio, rate = read_wav_mono(wav)
        assert silence_runs(audio, rate) == []

    # Phone list: "p uh t / m ay (pause 60 ms) b ah b (pause 300 ms) hh ow".
    layout = [
        ("sil", 0.20), ("P", 0.08), ("UH1", 0.20), ("T", 0.07), ("M", 0.09),
        ("AY1", 0.30), ("sil", 0.06), ("AA1", 0.25), ("B", 0.08), ("AH0", 0.15),
        ("B", 0.08), ("sil", 0.30), ("HH", 0.07), ("OW1", 0.30), ("sil", 0.10),
    ]
    phones, t = [], 0.0
    for label, d in layout:
        phones.append(Phone(t, t + d, label))
        t += d
    duration = t
    for fps in (12, 24):
        frames = build_frames(phones, duration, fps)
        assert len(frames) == math.ceil(duration * fps - 1e-9), (fps, len(frames))
        for p in phones:
            if strip_stress(p.label) in BILABIALS:
                hit = frames_overlapping(p.start, p.end, len(frames), fps)
                assert any(frames[k] in CLOSED_SHAPES for k in hit), (fps, p)
            elif is_silence(p.label) and p.dur >= MIN_PAUSE:
                for k in range(len(frames)):
                    if p.start <= (k + 0.5) / fps < p.end:
                        assert frames[k] == "rest", (fps, p, k, frames[k])
        # The 60 ms pause must not close the mouth.
        short = next(p for p in phones if is_silence(p.label) and abs(p.dur - 0.06) < 1e-9)
        k = int((short.start + short.end) / 2 * fps)
        assert frames[k] not in CLOSED_SHAPES, (fps, frames[k])
        # HH takes the shape of the next vowel (OW starts with "round_small").
        hh = next(p for p in phones if p.label == "HH")
        assert frames[int((hh.start + hh.end) / 2 * fps)] == "round_small", fps

    # Measured silence overrides a phoneme that runs across a pause.
    stretched = [Phone(0.0, 0.5, "AA1"), Phone(0.5, 1.0, "sil")]
    frames = build_frames(stretched, 1.0, 24, silences=[(0.3, 1.0)])
    assert frames[10] == "rest" and frames[3] != "rest", frames

    # Plan file round trip, and the table.
    doc = {"text": "t", "duration": duration, "source": "selftest",
           "phones": [[p.start, p.end, p.label] for p in phones]}
    plan = make_plan(doc, 24, duration, [])
    assert plan["shapes"] == SHAPES and len(plan["frames"]) == math.ceil(duration * 24 - 1e-9)
    assert "OW" in table_text() and "extended" in table_text()
    print("selftest OK: viseme_plan")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Turn timed phonemes into one mouth shape per video frame.")
    ap.add_argument("--phones", type=Path, help="phones file (JSON)")
    ap.add_argument("--wav", type=Path, help="16-bit PCM WAV of the audio (sets duration, finds silences)")
    ap.add_argument("--fps", type=int, default=24, help="video frame rate (default 24)")
    ap.add_argument("--out", type=Path, help="plan file to write")
    ap.add_argument("--cell", type=int, default=128, help="sheet cell size in pixels (default 128)")
    ap.add_argument("--background", default="#1e1e2e", help='background color (default "#1e1e2e")')
    ap.add_argument("--shape-map", type=Path, help="JSON file: Oculus viseme -> shape overrides")
    ap.add_argument("--no-audio-silence", action="store_true", help="ignore silences measured on the WAV")
    ap.add_argument("--table", action="store_true", help="print the ARPAbet -> Oculus -> shape table and exit")
    ap.add_argument("--selftest", action="store_true", help="run the built-in checks and exit")
    a = ap.parse_args(argv)

    if a.selftest:
        selftest()
        return 0
    if a.table:
        print(table_text())
        return 0
    if not a.phones or not a.out:
        ap.error("--phones and --out are required")
    try:
        doc = load_phones(a.phones)
        shape_map = check_shape_map(json.loads(a.shape_map.read_text())) if a.shape_map else None
        silences: list[tuple[float, float]] = []
        duration = float(doc.get("duration", 0.0))
        if a.wav:
            audio, rate = read_wav_mono(a.wav)
            duration = len(audio) / rate
            if not a.no_audio_silence:
                silences = silence_runs(audio, rate)
        if duration <= 0:
            raise ValueError("no duration: give --wav or a phones file with a 'duration'")
        plan = make_plan(doc, a.fps, duration, silences, shape_map, a.cell, a.background)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(plan) + "\n")
    except (OSError, ValueError, KeyError, wave.Error, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"{a.out}  {duration:.2f} s, {len(plan['frames'])} frames at {a.fps} fps, "
          f"{len(plan['runs'])} runs, {len(silences)} silences")
    return 0


if __name__ == "__main__":
    sys.exit(main())
