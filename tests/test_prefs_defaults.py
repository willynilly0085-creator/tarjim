"""Each default is what tarjim did before the setting existed (2026-11-09): a person who never
opens the settings gets the same subtitles, timing, hearing and files as before."""
from tarjim import media
from tarjim.asr import tolerated
from tarjim.dub import clone, mix
from tarjim.languages import LANGUAGES
from tarjim.lines import DASH
from tarjim.listen import chunks, coverage, merge
from tarjim.prefs.colour import rgb
from tarjim.prefs.folders import default_folder
from tarjim.prefs.model import resolve
from tarjim.prefs.table_look import LANDSCAPE_FONT, PORTRAIT_FONT
from tarjim.render import ass, mark, placement, voices
from tarjim.render.stages import MIN_STAGE
from tarjim.rules import DEFAULT_RULES
from tarjim.server import engine


def bgr(colour: str) -> str:
    """#RRGGBB as ASS writes a colour: blue, green, red."""
    red, green, blue = (int(c) for c in rgb(colour))
    return f"{blue:02X}{green:02X}{red:02X}"


def opacity(alpha: str) -> float:
    return (255 - int(alpha, 16)) / 255 * 100


def test_the_look_is_what_the_subtitle_file_drew() -> None:
    look = resolve({}, {}, "ar").look
    assert (look.style == "box") == ass.Canvas(1920, 1080).boxed
    assert (LANDSCAPE_FONT, PORTRAIT_FONT) == (0.058, 0.066)
    assert f"&H00{bgr(look.text_colour)}" == voices.MAIN
    assert ass.BOX_COLOUR[4:] == bgr(look.box_colour)
    assert round(opacity(ass.BOX_COLOUR[2:4])) == look.box_opacity
    assert f"&H00{bgr(look.outline_colour)}" == ass.OUTLINE_COLOUR
    assert round(opacity(ass.SHADOW_COLOUR[2:4])) == look.shadow
    assert f"\\blur{look.soft_edge}" == ass.SOFT_EDGE
    assert look.fade_ms == ass.FADE_MS and look.box_padding == 22
    others = tuple(f"&H{bgr(c)}&" for c in look.palette)
    assert others == voices.OTHERS and look.dialogue_dash == DASH


def test_the_margins_are_where_lines_were_placed() -> None:
    look = resolve({}, {}, "ar").look
    assert ass.Canvas(1920, 1080).margin_v == round(1080 * look.bottom_margin_wide / 100)
    assert ass.Canvas(1080, 1920).margin_v == round(1920 * look.bottom_margin_tall / 100)
    assert ass.Canvas(1920, 1080).margin_h == round(1920 * look.side_margin / 100)
    top = {False: look.top_margin_wide / 100, True: look.top_margin_tall / 100}
    assert top == placement.TOP_SAFE
    assert look.fade_ms <= MIN_STAGE * 1000 / 4


def test_the_mark_is_where_and_as_strong_as_it_was() -> None:
    look = resolve({}, {}, "ar").look
    assert look.mark_size == mark.LANDSCAPE_LOGO * 100
    assert mark.PORTRAIT_LOGO / mark.LANDSCAPE_LOGO == 6 / 4.5
    assert look.mark_opacity == mark.LOGO_OPACITY * 100 and look.mark


def test_reading_and_timing_are_the_rules_cues_were_cut_by() -> None:
    for code, lang in LANGUAGES.items():
        text = resolve({}, {}, code).text
        assert (text.reading_cps, text.line_chars) == (lang.reading_cps, lang.line_chars)
    timing = resolve({}, {}, "ar").timing
    for name in ("min_duration", "max_duration", "linger", "min_gap", "long_pause",
                 "join_gap", "min_readable", "cut_snap", "cut_dialogue_span"):
        assert getattr(timing, name) == getattr(DEFAULT_RULES, name), name
    assert timing.scene_sensitivity == media.SCENE_THRESHOLD
    assert DEFAULT_RULES.max_lines == 2 and not resolve({}, {}, "ar").text.one_line


def test_hearing_files_and_dubbing_are_as_before() -> None:
    prefs = resolve({}, {}, "ar")
    assert prefs.listen.passes == merge.PASSES
    assert prefs.listen.chunk_seconds == chunks.CHUNK_SECONDS
    assert prefs.listen.gap_seconds == coverage.GAP_SECONDS
    # the aligner reads strictly, as it did before the tolerant mode (2026-11-09)
    assert prefs.listen.aligner == tolerated.STRICT
    assert prefs.output.folder == default_folder() == str(engine.DOWNLOADS)
    assert prefs.dub.clone_steps == clone.STEPS and mix.VOICE_GAIN == 1.0
    assert prefs.dub.balance == 100 and prefs.output.enlarge == "1080"
