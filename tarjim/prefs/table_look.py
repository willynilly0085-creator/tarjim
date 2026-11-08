"""How a subtitle looks (2026-11-09). Each default is what tarjim drew before this setting
existed (render/ass.py, render/voices.py, render/placement.py, render/mark.py): sizes and
margins are parts of the picture, opacities and paddings are percentages."""
from tarjim.languages import language
from tarjim.prefs.make import ADVANCED, amount, basic, on_off, paint, per_language, pick
from tarjim.prefs.spec import Spec, Value

# The box and its letters: render/ass.py BOX_COLOUR &H50131415 (a warm near-black at about 69%
# cover), voices.MAIN &H00F0F5F7, OUTLINE_COLOUR &H00141414, SHADOW_COLOUR &H8C000000 (45%).
TEXT_COLOUR = "#F7F5F0"
BOX_COLOUR = "#151413"
OUTLINE_COLOUR = "#141414"
PALETTE = "#FFE066,#8FE3F5,#A8E6A1"  # render/voices.OTHERS, the second to fourth speaker
# auto: below, raised over the picture's own text for the whole video and for single lines
# (render/moments.py); steady: the whole video's place only; bottom and top: never moved.
POSITIONS = ("auto", "steady", "bottom", "top")
DASHES = ("- ", "– ", "— ")  # never empty: the dash is what tells two speakers apart
# The font size at 100%, as a part of the picture's short side (render/ass.py).
LANDSCAPE_FONT = 0.058
PORTRAIT_FONT = 0.066


def language_font(code: str) -> tuple[Value, float, float]:
    return language(code).font, 0.0, 0.0


BASIC_LOOK: tuple[Spec, ...] = (
    pick("look.style", "شكل الترجمة", ("box", "outline")),
    basic(amount("look.size_wide", "حجم الخط في الفيديو العرضي", 100, (80, 120, 5))),
    basic(amount("look.size_tall", "حجم الخط في الفيديو الطولي", 100, (80, 120, 5))),
    per_language("look.font", "نوع الخط", "font", language_font),
    paint("look.text_colour", "لون الكلام", TEXT_COLOUR),
    paint("look.box_colour", "لون الخلفية", BOX_COLOUR),
    # 60 at least: whatever sits under the subtitle must never spoil it (the owner, 2026-11-08).
    basic(amount("look.box_opacity", "قوة الخلفية", 69, (60, 100, 1))),
    pick("look.position", "مكان الترجمة", POSITIONS),
    on_off("look.speaker_colours", "لون لكل متكلم", True),
    on_off("look.mark", "شعار ترجم على الفيديو", True),
)

ADVANCED_LOOK: tuple[Spec, ...] = (
    on_off("look.bold", "خط عريض", True, ADVANCED),
    # At most 100 ms: a line is shown 0.4 s at the least (render/stages.MIN_STAGE), a quarter
    # of it fades; a line cut short by a scene change is capped again when it is drawn.
    amount("look.fade_ms", "سرعة ظهور واختفاء السطر", 90, (0, 100, 10)),
    # Up to 30%: the gap kept above the picture's text (placement.GAP) is 0.3 of the font.
    amount("look.box_padding", "المسافة بين الحروف وحافة الخلفية", 22, (10, 30, 1)),
    amount("look.outline_width", "سماكة حدود الحروف", 8, (4, 14, 1)),
    paint("look.outline_colour", "لون حدود الحروف", OUTLINE_COLOUR, ADVANCED),
    amount("look.shadow", "قوة الظل", 45, (0, 80, 5)),
    amount("look.soft_edge", "نعومة الحدود", 0.8, (0.0, 2.0, 0.2)),
    amount("look.bottom_margin_wide", "بعد الترجمة عن تحت في الفيديو العرضي", 7, (3, 20, 1)),
    amount("look.bottom_margin_tall", "بعد الترجمة عن تحت في الفيديو الطولي", 14, (10, 25, 1)),
    amount("look.top_margin_wide", "بعد الترجمة عن فوق في الفيديو العرضي", 5, (3, 15, 1)),
    amount("look.top_margin_tall", "بعد الترجمة عن فوق في الفيديو الطولي", 12, (10, 20, 1)),
    amount("look.side_margin", "المسافة من الجوانب", 6, (3, 12, 1)),
    Spec("look.speaker_palette", "ألوان المتكلم الثاني والثالث والرابع", "colours", PALETTE,
         tier=ADVANCED),
    on_off("look.staged_reveal", "كلام المتكلم الثاني يطلع لما يبدأ يتكلم", True, ADVANCED),
    amount("look.mark_size", "حجم الشعار", 4.5, (3.0, 7.0, 0.5)),
    amount("look.mark_opacity", "وضوح الشعار", 85, (40, 100, 5)),
    pick("look.mark_side", "جهة الشعار", ("left", "right"), ADVANCED),
    pick("look.dialogue_dash", "العلامة قبل كلام كل متكلم", DASHES, ADVANCED),
)

LOOK = BASIC_LOOK + ADVANCED_LOOK
