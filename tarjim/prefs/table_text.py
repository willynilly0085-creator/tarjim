"""How much a subtitle holds and how long it stays (2026-11-09). The defaults are rules.Rules,
languages.LANGUAGES (reading speed and line length per language), qa.py's warning at 1.25 times
the reading speed and media.SCENE_THRESHOLD."""
from tarjim.languages import language
from tarjim.prefs.make import ADVANCED, amount, basic, on_off, per_language, pick
from tarjim.prefs.spec import Spec, Value
from tarjim.rules import WIDE_EM, letter_width

# Reading speed, letters a second: Japanese is read by its characters (4 by default), Chinese
# and Korean by theirs (9 and 12), every spaced or Thai script by its letters (15 to 17).
SLOW_SCRIPT = 6.0


def wide(code: str) -> bool:
    return letter_width(language(code)) == WIDE_EM


def reading_speed(code: str) -> tuple[Value, float, float]:
    default = language(code).reading_cps
    if default < SLOW_SCRIPT:
        return default, 3.0, 6.0
    return (default, 6.0, 12.0) if wide(code) else (default, 12.0, 22.0)


def line_length(code: str) -> tuple[Value, float, float]:
    default = language(code).line_chars
    return (default, 12, 20) if wide(code) else (default, 32, 50)


TEXT: tuple[Spec, ...] = (
    per_language("text.reading_cps", "سرعة القراءة (حرف بالثانية)", "number", reading_speed),
    per_language("text.line_chars", "أقصى عدد حروف في السطر", "number", line_length),
    pick("text.reading_warning", "متى ينبهك التقرير إن السطر سريع", (1.25, 1.0, 1.5),
         ADVANCED),
    # One line instead of two, the short-video style: an exchange needs a line per speaker.
    on_off("text.one_line", "سطر واحد بس", False, ADVANCED),
)

TIMING: tuple[Spec, ...] = (
    # 0.6 to 1.0: a later line waits for the one before it to have been shown this long, so a
    # longer floor shows quick replies more than a second after they are said.
    basic(amount("timing.min_duration", "أقل مدة يبقى فيها السطر (ثانية)", 0.8,
                 (0.6, 1.0, 0.1))),
    basic(amount("timing.max_duration", "أطول مدة للسطر (ثانية)", 6.0, (3.5, 8.0, 0.5))),
    basic(amount("timing.linger", "كم يبقى السطر بعد ما يسكت المتكلم (ثانية)", 0.4,
                 (0.0, 1.0, 0.1))),
    amount("timing.min_gap", "الفراغ بين سطر وسطر (ثانية)", 0.083, (0.04, 0.25, 0.0)),
    amount("timing.long_pause", "سكتة بهالطول تبدأ سطر جديد (ثانية)", 2.5, (1.0, 4.0, 0.1)),
    amount("timing.join_gap", "أطول سكتة يندمج عبرها الكلام القصير (ثانية)", 1.0,
           (0.3, 2.0, 0.1)),
    amount("timing.min_readable", "الكلام الأقصر من كذا يندمج مع اللي جنبه (ثانية)", 0.9,
           (0.5, 1.5, 0.1)),
    on_off("timing.end_at_cuts", "السطر ينتهي لما تتغير اللقطة", True, ADVANCED),
    amount("timing.cut_snap", "قوة التصاق السطر بتغير اللقطة (ثانية)", 0.35, (0.0, 0.6, 0.05)),
    pick("timing.scene_sensitivity", "حساسية كشف تغير اللقطة", (0.25, 0.15, 0.35, 0.5),
         ADVANCED),
    amount("timing.cut_dialogue_span", "حوار سريع يعدي تغير اللقطة بسطر واحد (ثانية)", 2.0,
           (0.0, 3.0, 0.5)),
    on_off("timing.dialogue_cues", "متكلمين اثنين بنفس السطر بشرطة", True, ADVANCED),
)
