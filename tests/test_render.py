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


def test_light_videos_get_one_box_behind_the_whole_subtitle() -> None:
    from tarjim.render.ass import Canvas, render_ass

    dark = render_ass([], Canvas(1920, 1080))
    light = render_ass([], Canvas(1920, 1080, bright=True))
    assert ",1,5,2,2," in dark and "&H00141414" in dark
    assert ",4,1,14,2," in light and light.count("&H3A141414") == 2


def test_brightness_is_read_from_the_ffmpeg_report() -> None:
    from tarjim.media import mean_brightness

    report = "lavfi.signalstats.YAVG=200.5\nnoise\nlavfi.signalstats.YAVG=180.5\n"
    assert mean_brightness(report) == 190.5
    assert mean_brightness("") == 0.0


def test_a_boxed_dialogue_hides_only_the_letters_of_the_line_still_to_come() -> None:
    from tarjim.models import Cue, Word
    from tarjim.render.ass import Canvas, render_ass

    first, second = [Word("Nice", 0.0, 0.5, "S1")], [Word("idea", 1.5, 2.0, "S2")]
    cue = Cue(0.0, 3.0, first + second, "- one || - two", parts=[first, second])
    boxed = render_ass([cue], Canvas(1920, 1080, bright=True))
    assert r"\1a&HFF&\3a&HFF&" in boxed and r"\alpha" not in boxed
    assert r"\alpha&HFF&" in render_ass([cue], Canvas(1920, 1080))
