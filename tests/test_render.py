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
    assert "0:00:46.80" in events[0] and "\\alpha&HFF&}" in events[0]
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
