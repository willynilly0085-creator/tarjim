"""Synthetic ground-truth scenarios for the timing bench.

A line is (speaker, text, gap_before_s, overlap_s): it starts gap_before_s after the
moment everyone placed so far has stopped talking, minus overlap_s (so overlap_s > 0
makes it talk over the previous line). Speakers are "A", "B", "C"; "D" is a background voice.

Background lines (Scenario.background) are placed on their own timeline from
background_lead_s, `background_db` under the active speech, and marked "background" in the
truth: speech that is in the sound but must not be subtitled. A scenario with `vad_below` is
remade by make.py with the bed raised until the voice detector's recall on the truth speech is
below that share (or make.py fails).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import lines_ar
import lines_en
import lines_en2
import lines_en3

Line = tuple[str, str, float, float]


@dataclass(frozen=True)
class Voice:
    """A OneCore voice; pitch/rate are engine options, shift is an ffmpeg
    asetrate+atempo factor (moves pitch and formants, keeps the duration)."""
    base: str
    pitch: float = 1.0
    rate: float = 1.0
    shift: float = 1.0


DAVID = Voice("DavidM")
MARK = Voice("MarkM", pitch=0.95)
ZIRA = Voice("ZiraM")
DAVID_DEEP = Voice("DavidM", pitch=0.9, rate=0.95, shift=0.84)
NAAYF = Voice("NaayfM")
NAAYF_HIGH = Voice("NaayfM", pitch=1.1, rate=1.05, shift=1.22)
MARK_CHANT = Voice("MarkM", pitch=0.95, rate=0.7, shift=1.25)
ZIRA_CHANT = Voice("ZiraM", rate=0.7, shift=1.25)


@dataclass
class Scenario:
    name: str
    language: str
    lines: list[Line]
    bed: str = "none"  # "none" | "music" | "noise"
    bed_db: float = -12.0  # bed RMS relative to active speech RMS
    faults: list[str] = field(default_factory=list)  # filled/used by the runner
    voices: dict[str, Voice] = field(default_factory=dict)
    lead_s: float = 1.0  # silence before the first line
    tail_s: float = 1.5  # silence after the last word; 0 = clip ends on speech
    note: str = ""
    background: list[Line] = field(default_factory=list)  # in the sound, never subtitled
    background_db: float = -20.0  # background RMS relative to the active speech RMS
    background_lead_s: float = 2.0
    vad_below: float | None = None  # make.py raises bed_db until VAD recall is below this
    longest_s: float = 240.0  # make.py flags a clip longer than this


ROW = re.compile(r"^([A-Z])(?:\s+([+-]\d+(?:\.\d+)?))?:\s*(.+)$")
DEFAULT_GAPS = (0.45, 0.6, 0.35, 0.75, 0.5)


def script(text: str) -> list[Line]:
    """Parse `S: text`, `S +gap: text`, `S -overlap: text` rows."""
    out: list[Line] = []
    for row in (r.strip() for r in text.strip().splitlines()):
        if not row:  # two scripts joined end to end
            continue
        m = ROW.match(row)
        if not m:
            raise ValueError(f"bad row: {row!r}")
        speaker, num, said = m.groups()
        gap, over = DEFAULT_GAPS[len(out) % len(DEFAULT_GAPS)], 0.0
        if num is not None:
            value = float(num)
            gap, over = (value, 0.0) if value >= 0 else (0.0, -value)
        out.append((speaker, said, 0.0 if not out else gap, over))
    return out


EN2 = {"A": MARK, "B": ZIRA}
EN3 = {"A": DAVID, "B": ZIRA, "C": MARK}

SCENARIOS: list[Scenario] = [
    Scenario("en_monologue", "English", script(lines_en.MONOLOGUE), voices={"A": DAVID},
             note="one speaker, paced talk"),
    Scenario("en_interview_quick", "English", script(lines_en.INTERVIEW), voices=EN2,
             note="two speakers, one-word replies (Yes./Really?/Right.) and a backchannel"),
    Scenario("en_panel_three", "English", script(lines_en.PANEL), voices=EN3,
             note="moderator and two guests"),
    Scenario("en_debate_overlap", "English", script(lines_en.DEBATE),
             voices={"A": MARK, "B": ZIRA, "C": DAVID}, note="heated, overlaps 0.3-1.5 s"),
    Scenario("en_long_three_pieces", "English", script(lines_en2.LONG), voices=EN3,
             note="~220 s, crosses three 75 s pieces"),
    Scenario("en_silence_middle", "English", script(lines_en.SILENCE),
             voices={"A": ZIRA, "B": DAVID}, note="30 s of silence mid clip"),
    Scenario("en_interview_music", "English", script(lines_en.INTERVIEW), "music", -12.0,
             voices=EN2, note="interview script under a music bed at -12 dB"),
    Scenario("en_panel_noise", "English", script(lines_en.PANEL), "noise", -15.0,
             voices=EN3, note="panel script under pink noise at -15 dB"),
    Scenario("en_refrain_twice", "English", script(lines_en.REFRAIN), voices=EN2,
             note="same line said twice back to back (same and cross speaker)"),
    Scenario("en_fourth_voice", "English", script(lines_en2.FOURTH),
             voices={"A": DAVID, "B": ZIRA, "C": DAVID_DEEP},
             note="C is A's voice shifted down: a fourth voice from the same base"),
    Scenario("ar_dialogue", "Arabic", script(lines_ar.DIALOGUE),
             voices={"A": NAAYF, "B": NAAYF_HIGH}, note="Arabic two-speaker dialogue"),
    Scenario("en_ends_on_speech", "English", script(lines_en2.ENDING),
             voices={"A": ZIRA, "B": MARK}, tail_s=0.0, note="speech runs to the last sample"),
    Scenario("ar_news_monologue", "Arabic", script(lines_ar.NEWS), voices={"A": NAAYF},
             note="Arabic news read by one speaker"),
    Scenario("en_chant_bed", "English", script(lines_en.INTERVIEW), "music", 0.0,
             voices={"A": MARK_CHANT, "B": ZIRA_CHANT}, vad_below=0.8,
             note="interview script, voices shifted x1.25 at rate 0.7 under music; the bed is "
                  "raised from 0 dB SNR until the voice detector misses 20% of the speech"),
    Scenario("en_long_seven", "English", script(lines_en2.LONG + lines_en3.SEVEN), voices=EN3,
             longest_s=480.0, note="~7 min, three voices, five or more 75 s pieces"),
    Scenario("en_refrain_close", "English", script(lines_en3.REFRAIN_CLOSE), voices=EN2,
             note="one sentence said twice ~20 s apart inside one piece"),
    Scenario("background_speech", "English", script(lines_en3.MEETING),
             voices={"A": DAVID, "B": ZIRA, "C": MARK, "D": DAVID_DEEP},
             background=script(lines_en3.RADIO), background_db=-20.0,
             note="a meeting with a radio 20 dB under it; the radio is never subtitled"),
    Scenario("mixed_en_ar", "English", script(lines_en3.MIXED), voices={"A": DAVID, "B": NAAYF},
             note="English host, Arabic guest, each in their own language"),
]


def by_name(name: str) -> Scenario:
    for s in SCENARIOS:
        if s.name == name:
            return s
    raise KeyError(name)
