"""The target language's rules and the picture's shape reach every step that cuts and draws
subtitles, and colours follow the parts a translation really has (2026-11-08)."""
from pathlib import Path

import pytest

from tarjim import media, pipeline
from tarjim.job import Job
from tarjim.languages import language
from tarjim.models import Cue, Word
from tarjim.render.stages import reveal_at
from tarjim.render.voices import line_voices
from tarjim.rules import DEFAULT_RULES, Rules, rules_for

YELLOW = "&H66E0FF&"


def exchange(text: str) -> Cue:
    first = [Word("Did", 0.0, 0.3, "S1"), Word("you", 0.3, 0.6, "S1"), Word("go?", 0.6, 1.0, "S1")]
    second = [Word("Yes,", 1.6, 1.9, "S2"), Word("twice.", 1.9, 2.4, "S2")]
    return Cue(0.0, 3.0, first + second, text=text, parts=[first, second])


def run_with(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: tuple[int, int],
             target: str = "ja") -> tuple[Job, list[Rules]]:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    seen: list[Rules] = []

    def built(_words: list[Word], _cuts: list[float], rules: Rules = DEFAULT_RULES) -> list[Cue]:
        seen.append(rules)
        return []

    def translated(_job: Job, cues: list[Cue], rules: Rules | None = None,
                   _cuts: list[float] | None = None) -> list[Cue]:
        seen.append(rules or DEFAULT_RULES)
        return cues

    heard = type("Heard", (), {"words": []})()
    monkeypatch.setattr(pipeline.media, "check_readable", lambda _v: None)
    monkeypatch.setattr(pipeline.media, "probe", lambda _v: media.VideoInfo(*size, 9.0))
    monkeypatch.setattr(pipeline, "transcript_for", lambda _j, _r: heard)
    monkeypatch.setattr(pipeline, "cuts_for", lambda _j: [])
    monkeypatch.setattr(pipeline, "build_cues", built)
    monkeypatch.setattr(pipeline, "translate", translated)
    monkeypatch.setattr(pipeline, "write_outputs", lambda *_a: None)
    job = Job(video, target=target, cache_dir=tmp_path / "work", out_dir=tmp_path / "out")
    pipeline.run(job)
    return job, seen


def test_the_target_languages_rules_cut_the_subtitles(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job, seen = run_with(tmp_path, monkeypatch, (1920, 1080))
    assert seen == [job.rules, job.rules] and job.rules.line_chars == 13


def test_a_standing_picture_gets_shorter_lines_before_anything_is_cut(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _job, seen = run_with(tmp_path, monkeypatch, (1080, 1920), target="ar")
    built, translated = seen
    assert built == translated
    assert built.line_chars < 42 and built.max_source_chars < 84


def two_lines_fit(rules: Rules, width: int, height: int) -> bool:
    from tarjim.render.ass import Canvas

    canvas = Canvas(width, height)
    usable = width - 2 * canvas.margin_h - 2 * canvas.shadow
    return rules.line_chars * canvas.font_size * rules.char_em <= usable


@pytest.mark.parametrize("code", ["ar", "en", "zh", "ja", "ko", "th", "hi", "xx"])
@pytest.mark.parametrize("size", [(1080, 1920), (720, 1280), (1080, 1080), (1920, 1080),
                                  (640, 480), (1080, 2400)])
def test_every_line_fits_the_picture_it_is_drawn_on(code: str, size: tuple[int, int]) -> None:
    from tarjim.render.room import fitted

    rules = fitted(rules_for(language(code)), *size)
    assert two_lines_fit(rules, *size)
    assert rules.line_chars <= rules_for(language(code)).line_chars


def test_a_wide_picture_keeps_the_usual_lines() -> None:
    from tarjim.render.room import fitted

    for code in ("ar", "en", "zh", "ja", "th"):
        assert fitted(rules_for(language(code)), 1920, 1080) == rules_for(language(code))
    assert fitted(DEFAULT_RULES, 0, 0) == DEFAULT_RULES  # a sound file has no picture


def test_chinese_and_korean_letters_count_as_wide() -> None:
    assert rules_for(language("zh")).char_em > rules_for(language("ar")).char_em
    assert rules_for(language("ko")).char_em == rules_for(language("ja")).char_em


def test_one_translation_wrapped_in_two_lines_keeps_one_colour() -> None:
    cue = exchange("ذهبت إلى السوق مرتين في الأسبوع الماضي مع أخي الكبير وأولاده")
    colours = line_voices(cue, 2, {"S2": YELLOW})
    assert colours[0] == colours[1]


def test_each_part_of_an_exchange_keeps_its_speakers_colour() -> None:
    colours = line_voices(exchange("رحت؟ || إيه، مرتين."), 2, {"S2": YELLOW})
    assert colours[1] == f"{{\\c{YELLOW}}}" and colours[0] != colours[1]


def test_one_translation_wrapped_in_two_lines_shows_all_at_once() -> None:
    cue = exchange("ذهبت إلى السوق مرتين في الأسبوع الماضي مع أخي الكبير وأولاده")
    assert reveal_at(cue, DEFAULT_RULES) is None
    assert reveal_at(exchange("رحت؟ || إيه، مرتين."), DEFAULT_RULES) == 1.6


def test_a_half_answered_exchange_shows_all_at_once() -> None:
    assert reveal_at(exchange("رحت؟ || "), rules_for(language("ja"))) is None


def test_each_part_of_an_exchange_has_a_budget_of_one_line() -> None:
    rules = rules_for(language("ar"))
    assert rules.budgets(5.0, 1) == [rules.char_budget(5.0)]
    each = rules.budgets(5.0, 2)
    assert len(each) == 2 and all(b <= rules.line_chars - 2 for b in each)


def test_the_translator_is_told_each_parts_budget() -> None:
    from tarjim.translate.prompt import Brief, format_item

    line = format_item(1, exchange(""), Brief(language("ar"), "saudi", DEFAULT_RULES))
    per = DEFAULT_RULES.budgets(3.0, 2)
    assert f"budget={per[0]}+{per[1]}]" in line


def test_a_long_turn_is_not_glued_to_a_quick_reply_it_cannot_share_a_screen_with() -> None:
    from tarjim.segment import build_cues

    long = ["so", "the", "thing", "about", "the", "market", "is", "that", "nobody", "really",
            "goes", "there", "anymore"]
    turn = [Word(w, k * 0.3, k * 0.3 + 0.25, "S1") for k, w in enumerate(long)]
    reply = Word("Yeah.", turn[-1].end + 0.2, turn[-1].end + 0.5, "S2")
    cues = build_cues([*turn, reply], cuts=[])
    assert all(len(" ".join(w.text for w in part)) <= DEFAULT_RULES.part_chars
               for c in cues if c.is_dialogue for part in c.parts)


def test_qa_names_a_line_too_short_to_read() -> None:
    from tarjim.qa import check

    issues = check([Cue(1.0, 1.2, [Word("Hi.", 1.0, 1.2)], text="هلا")])
    assert "too_short" in {i.kind for i in issues}


def test_the_picture_is_probed_once_a_run(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-11-08: the run probed the picture for the line length and again to draw it."""
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"x")
    probed: list[Path] = []

    def probe(path: Path) -> media.VideoInfo:
        probed.append(path)
        return media.VideoInfo(1080, 1920, 9.0)

    heard = type("Heard", (), {"words": [Word("Hi.", 0.0, 0.5)]})()
    monkeypatch.setattr(pipeline.media, "check_readable", lambda _v: None)
    monkeypatch.setattr(pipeline.media, "probe", probe)
    monkeypatch.setattr(pipeline, "transcript_for", lambda _j, _r: heard)
    monkeypatch.setattr(pipeline, "cuts_for", lambda _j: [])
    monkeypatch.setattr(pipeline, "translate", lambda _j, cues, *_a: cues)
    monkeypatch.setattr(pipeline, "placed", lambda _j, _c, canvas, _d: canvas)
    monkeypatch.setattr(pipeline, "moved", lambda _j, _c, canvas, _m: canvas)
    job = Job(video, burn=False, cache_dir=tmp_path / "work", out_dir=tmp_path)
    pipeline.run(job)
    assert probed == [video] and job.output(".ass").exists()
