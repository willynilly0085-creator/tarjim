from tarjim.models import Cue, Word
from tarjim.render.ass import Canvas, render_ass
from tarjim.render.srt import RLM, render_srt


def test_portrait_gets_bigger_text_and_higher_margin() -> None:
    portrait, landscape = Canvas(720, 1280), Canvas(1920, 1080)
    assert portrait.font_size == 48
    assert landscape.font_size == 63
    assert portrait.margin_v > landscape.margin_v


def test_ass_uses_real_resolution_and_dialogue_dashes() -> None:
    cues = [Cue(1.0, 2.5, text="إيه؟ || إيه.")]
    ass = render_ass(cues, Canvas(720, 1280))
    assert "PlayResX: 720" in ass and "PlayResY: 1280" in ass
    assert "- إيه؟" in ass and "\\N" in ass


def dialogue(reply_at: float) -> Cue:
    ask, reply = [Word("Once", 44.2, 45.1, "S5")], [Word("Once?", reply_at, 47.3, "S1")]
    return Cue(44.2, 47.8, ask + reply, text="مرة بالشهر. || مرة بالشهر؟", parts=[ask, reply])


def test_reply_line_appears_when_its_speaker_starts_talking() -> None:
    ass = render_ass([dialogue(46.8)], Canvas(720, 1280))
    events = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
    assert len(events) == 2
    assert "0:00:46.80" in events[0] and "\\1a&HFF&\\3a&HFF&}" in events[0]
    assert events[1].startswith("Dialogue: 0,0:00:46.80,0:00:47.80")
    srt = render_srt([dialogue(46.8)])
    first = srt.split("\n\n")[0].splitlines()
    assert first[1] == "00:00:44,200 --> 00:00:46,800"
    assert [line.strip(RLM) for line in first[2:]] == ["- مرة بالشهر."]


def test_reply_right_at_the_start_shows_both_lines_together() -> None:
    events = [e for e in render_ass([dialogue(44.3)], Canvas(720, 1280)).splitlines()
              if e.startswith("Dialogue:")]
    assert len(events) == 1


def test_srt_skips_empty_cues_and_numbers_the_rest() -> None:
    srt = render_srt([Cue(0, 1, text=""), Cue(1, 2, text="حلو")])
    assert srt.startswith("1\n00:00:01,000 --> 00:00:02,000")


def test_every_subtitle_sits_on_one_see_through_box() -> None:
    from tarjim.render.ass import Canvas, render_ass

    boxed = render_ass([], Canvas(1920, 1080))
    outlined = render_ass([], Canvas(1920, 1080, boxed=False))
    # 2026-11-10: a dark edge round the letters, the box behind them
    assert ",4,3.8,13.9,2," in boxed and "&H00141414,&H50131415" in boxed
    assert ",1,5,2,2," in outlined and "&H00141414" in outlined


def test_a_boxed_dialogue_hides_only_the_letters_of_the_line_still_to_come() -> None:
    from tarjim.models import Cue, Word
    from tarjim.render.ass import Canvas, render_ass

    first, second = [Word("Nice", 0.0, 0.5, "S1")], [Word("idea", 1.5, 2.0, "S2")]
    cue = Cue(0.0, 3.0, first + second, "- one || - two", parts=[first, second])
    boxed = render_ass([cue], Canvas(1920, 1080))
    assert r"\1a&HFF&\3a&HFF&" in boxed and r"\alpha" not in boxed
    assert r"\alpha&HFF&" in render_ass([cue], Canvas(1920, 1080, boxed=False))


def test_arabic_subtitles_let_libass_order_mixed_latin_words() -> None:
    ass = render_ass([Cue(0, 2, text="افتح YouTube الآن")], Canvas(1280, 720))
    style = next(line for line in ass.splitlines() if line.startswith("Style:"))
    assert style.endswith(",-1")
    assert "WrapStyle: 0" in ass  # a line too wide for the picture still wraps


def test_a_backslash_in_the_text_is_not_an_ass_command() -> None:
    ass = render_ass([Cue(0, 2, text=r"C:\Next \N folder")], Canvas(1280, 720))
    event = next(line for line in ass.splitlines() if line.startswith("Dialogue:"))
    assert "\\" not in event.split(",,", 1)[1].split("}", 1)[1]


def test_the_letters_edge_and_box_are_the_same_share_at_every_picture_size() -> None:
    """2026-11-10: the edge was one unit whatever the picture, clear at 270 lines and next to
    nothing at 1080. Edge and padding are a share of the letter, so the look does not change."""
    for width, height in ((480, 270), (1280, 720), (1920, 1080), (270, 480), (1080, 1920)):
        canvas = Canvas(width, height)
        assert abs(canvas.outline / canvas.font_size - 0.06) < 0.005
        assert abs(canvas.shadow / canvas.font_size - 0.22) < 0.005
