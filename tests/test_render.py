from tarjim.models import Cue
from tarjim.render.ass import Canvas, render_ass
from tarjim.render.srt import render_srt


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


def test_srt_skips_empty_cues_and_numbers_the_rest() -> None:
    srt = render_srt([Cue(0, 1, text=""), Cue(1, 2, text="حلو")])
    assert srt.startswith("1\n00:00:01,000 --> 00:00:02,000")
