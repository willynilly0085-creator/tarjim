"""Each look setting changes what the subtitle file draws, and nothing else (2026-11-09); with
nothing changed, the file is the one tarjim drew before the settings."""
from dataclasses import replace
from typing import Any

from tarjim.languages import language
from tarjim.models import Cue, Word
from tarjim.prefs.model import Prefs, resolve
from tarjim.render import mark
from tarjim.render.ass import Canvas, render_ass
from tarjim.render.placement import chosen_place, place, size
from tarjim.rules import rules_for

ASK = [Word("Same", 0.0, 0.5, "S2"), Word("here", 0.5, 0.9, "S2")]
REPLY = [Word("Exactly", 1.2, 1.9, "S1")]
MAIN = [Word(w, 3.0 + k * 0.3, 3.2 + k * 0.3, "S1") for k, w in enumerate("abcdef")]
CUES = [Cue(0.0, 2.5, ASK + REPLY, text="نفس الشيء || بالضبط", parts=[ASK, REPLY]),
        Cue(3.0, 6.0, MAIN, text="هذا كلام المتكلم الأول", parts=[MAIN])]
# The style line tarjim writes with nothing changed, field for field: since 1.0.70 a dark edge
# round the letters on the box, edge and padding as shares of the letter (2026-11-10).
STYLE = ("Style: Default,Dubai,63,&H00F0F5F7,&H00F0F5F7,&H00141414,&H50131415,-1,0,0,0,"
         "100,100,0,0,4,3.8,13.9,2,115,115,76,-1")
WIDE = (1920, 1080)


def prefs(**changed: Any) -> Prefs:
    return resolve({f"look.{k}": v for k, v in changed.items()}, {}, "ar")


def canvas(chosen: Prefs, shape: tuple[int, int] = WIDE) -> Canvas:
    return Canvas.drawn(shape, chosen.look, "Dubai")


def drawn(chosen: Prefs) -> list[str]:
    return render_ass(CUES, canvas(chosen), rules_for(language("ar"), chosen)).splitlines()


def changed_lines(chosen: Prefs) -> list[tuple[str, str]]:
    before, after = drawn(prefs()), drawn(chosen)
    assert len(before) == len(after)
    return [(a, b) for a, b in zip(before, after, strict=True) if a != b]


def test_nothing_changed_draws_the_file_drawn_before() -> None:
    assert STYLE in drawn(prefs())
    assert canvas(prefs()) == Canvas(1920, 1080)


def test_the_style_line_alone_takes_size_bold_box_and_margins() -> None:
    for chosen, at, value in (
            (prefs(size_wide=120), 2, "75"), (prefs(bold=False), 7, "0"),
            (prefs(box_colour="#000000"), 6, "&H50000000"),
            (prefs(box_opacity=100), 6, "&H00131415"), (prefs(box_padding=30), 17, "18.9"),
            (prefs(bottom_margin_wide=10), 21, "108"), (prefs(side_margin=10), 19, "192")):
        lines = changed_lines(chosen)
        assert [a for a, _b in lines] == [STYLE], chosen.look
        assert lines[0][1].split(",")[at] == value, chosen.look


def test_the_text_colour_is_the_styles_and_every_main_speakers_line() -> None:
    lines = changed_lines(prefs(text_colour="#FFFFFF"))
    assert lines[0] == (STYLE, STYLE.replace("&H00F0F5F7", "&H00FFFFFF"))
    assert all("\\c&HF0F5F7&" in a and "\\c&HFFFFFF&" in b for a, b in lines[1:])


def test_a_tall_size_leaves_a_wide_video_alone_and_grows_a_tall_one() -> None:
    assert changed_lines(prefs(size_tall=120)) == []
    tall = canvas(prefs(size_tall=120), (1080, 1920))
    assert tall.font_size == round(1080 * 0.066 * 1.2) != canvas(prefs(), (1080, 1920)).font_size


def test_outlined_letters_take_their_own_width_colour_shadow_and_softness() -> None:
    plain = canvas(prefs(style="outline"))
    assert not plain.boxed and plain.outline == 5
    text = "\n".join(drawn(prefs(style="outline", outline_width=14, outline_colour="#202020",
                                 shadow=0, soft_edge=1.6)))
    assert ",&H00202020,&HFF000000," in text and ",1,9,4,2," in text and "\\blur1.6" in text
    assert changed_lines(prefs(outline_width=14, soft_edge=1.6, shadow=0)) == []


def test_speaker_colours_turn_off_and_take_the_persons_palette() -> None:
    assert "\\c&H66E0FF&" in "\n".join(drawn(prefs()))
    assert "\\c&H" not in "\n".join(drawn(prefs(speaker_colours=False)))
    assert "\\c&H00FFFF&" in "\n".join(drawn(prefs(speaker_palette="#FFFF00")))


def test_the_second_speaker_shows_at_once_and_with_the_persons_dash() -> None:
    staged = [e for e in drawn(prefs()) if e.startswith("Dialogue:")]
    together = [e for e in drawn(prefs(staged_reveal=False)) if e.startswith("Dialogue:")]
    assert len(staged) == 3 and len(together) == 2
    assert "— نفس" in "\n".join(drawn(prefs(dialogue_dash="— ")))


def test_a_fade_is_the_persons_and_never_more_than_a_quarter_of_its_line() -> None:
    assert "\\fad(50,50)" in "\n".join(drawn(prefs(fade_ms=50)))
    assert "\\fad(90,90)" in "\n".join(drawn(prefs()))
    # cut to 0.2 s by a scene change: 50 ms each way at most
    assert "\\fad(50,50)" in render_ass([Cue(0.0, 0.2, text="قصير")], Canvas(1920, 1080))


def test_no_fade_shows_the_second_speaker_at_once() -> None:
    # libass reads \t(0,0,...) as the whole event, so the reveal crawled over it (2026-11-09)
    arriving = [e for e in drawn(prefs(fade_ms=0)) if "بالضبط" in e][-1]
    assert "\\t(" not in arriving and "{\\1a&H00&\\3a&H00&}{\\c&HF0F5F7&}" in arriving
    assert "\\t(0,90,\\1a&H00&\\3a&H00&)" in "\n".join(drawn(prefs()))


def test_the_gap_over_the_pictures_text_follows_the_padding() -> None:
    assert size(Canvas(1920, 1080))[1] == round(0.3 * 63)
    assert size(canvas(prefs(box_padding=30)))[1] == round(0.38 * 63)


def test_the_place_is_the_persons_choice() -> None:
    caption = [(0.85, 0.95)]
    usual = canvas(prefs())
    assert chosen_place(caption, usual) == place(caption, usual) != usual
    steady = chosen_place(caption, canvas(prefs(position="steady")))
    assert steady.margin_v == place(caption, usual).margin_v
    bottom = canvas(prefs(position="bottom"))
    assert chosen_place(caption, bottom) == bottom
    top = chosen_place(caption, canvas(prefs(position="top", top_margin_wide=9)))
    assert top.top and top.margin_v == round(1080 * 0.09)


def test_the_mark_takes_its_size_strength_and_side() -> None:
    usual = mark.place_mark(Canvas(1920, 1080))
    assert mark.place_mark(canvas(prefs(mark_size=6.0))).logo == round(1080 * 0.06)
    right = mark.place_mark(canvas(prefs(mark_side="right")))
    assert right.x == 1920 - usual.x - usual.logo and right.y == usual.y
    assert "\\an6\\pos(" in mark.with_mark("a\n\n[Events]\n", right)
    assert right.text_x < right.x and "\\an6" not in mark.with_mark("a\n\n[Events]\n", usual)
    faint = mark.place_mark(canvas(prefs(mark_opacity=40)))
    assert "aa=0.4[logo]" in mark.overlay(faint, "v")
    assert "aa=0.85[logo]" in mark.overlay(usual, "v")
    assert "&H26FFFFFF" in mark.with_mark("a\n\n[Events]\n", usual)
    assert "&H26FFFFFF" not in mark.with_mark("a\n\n[Events]\n", faint)
    assert mark.mark_for(canvas(prefs(mark=False))) is None


def test_a_layout_change_is_a_new_layout() -> None:
    usual = Canvas(1920, 1080)
    for chosen in (prefs(side_margin=10), prefs(size_wide=90), prefs(position="top"),
                   prefs(box_padding=30), prefs(bottom_margin_wide=12)):
        assert canvas(chosen).layout != usual.layout
    assert replace(usual, margin=40).layout == usual.layout
    assert canvas(prefs(text_colour="#FFFFFF")).layout == usual.layout
