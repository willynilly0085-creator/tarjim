from tarjim.languages import language
from tarjim.lines import display_lines
from tarjim.models import Cue
from tarjim.render.srt import RLM, render_srt
from tarjim.rules import rules_for


def test_unknown_code_still_works_left_to_right() -> None:
    other = language("xx")
    assert other.name == "xx" and not other.rtl


def test_japanese_breaks_between_characters_within_its_short_line() -> None:
    rules = rules_for(language("ja"))
    lines = display_lines("今日はとても暑いですね。明日は雨が降るそうです", rules)
    assert len(lines) == 2
    assert all(len(line) <= rules.line_chars for line in lines)
    assert lines[0].endswith("。")


def test_english_subtitles_carry_no_right_to_left_marks() -> None:
    srt = render_srt([Cue(0, 1, text="Once a month.")], rules_for(language("en")))
    assert RLM not in srt
    arabic = render_srt([Cue(0, 1, text="مرة بالشهر")], rules_for(language("ar")))
    assert RLM in arabic
