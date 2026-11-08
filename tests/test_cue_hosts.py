"""Where a reply goes, how long an exchange's parts may grow, and how lines break (2026-11-08):
a reply sits in the subtitle whose time holds it, a part never runs onto a third line, a reply
part is never glued to the next subtitle's words, the .srt breaks lines as the picture does, and
an unspaced script never starts a line with a mark that belongs on the letter before it."""
import unicodedata
from pathlib import Path

import pytest

from tarjim import media, pipeline
from tarjim.dialogue import split_at, take_reply, with_replies
from tarjim.fit import fit_timing
from tarjim.job import Job
from tarjim.languages import language
from tarjim.lines import balance_lines, display_lines
from tarjim.models import Cue, Word
from tarjim.render.room import fitted
from tarjim.rules import DEFAULT_RULES, Rules, rules_for
from tarjim.segment import build_cues


def spread(text: str, start: float, end: float, who: str = "") -> list[Word]:
    tokens = text.split()
    step = (end - start) / len(tokens)
    return [Word(token, start + k * step, start + (k + 1) * step - 0.02, who)
            for k, token in enumerate(tokens)]


def holding(cues: list[Cue], text: str) -> Cue:
    return next(c for c in cues if any(w.text == text for w in c.words))


def parts_of(cue: Cue) -> list[list[str]]:
    return [[w.text for w in part] for part in cue.parts]


@pytest.mark.parametrize("order", ["reply last", "reply in time"])
def test_a_reply_after_a_finished_sentence_goes_with_the_turn_it_is_said_over(
        order: str) -> None:
    first = spread("I went to the market today.", 0.0, 2.0, "S1")
    reply = spread("Really?", 2.3, 2.8, "S2")
    then = spread("Then I saw my old teacher there", 2.5, 4.5, "S1")
    words = [*first, *then, *reply] if order == "reply last" else [*first, *reply, *then]
    cues = build_cues(words, cuts=[])
    shown = holding(cues, "Really?")
    assert shown.start >= 2.0 and shown.start <= 2.3 + 1e-9 and shown.end >= 2.8
    assert "today." not in [w.text for w in shown.words]
    assert holding(cues, "today.").end <= 2.3


@pytest.mark.parametrize("rules", [DEFAULT_RULES, fitted(DEFAULT_RULES, 1080, 1920)])
def test_a_reply_before_a_long_line_is_not_joined_back_over_the_silence(rules: Rules) -> None:
    first = spread("I went to the market today.", 0.0, 2.0, "S1")
    reply = spread("Really?", 2.3, 2.8, "S2")
    then = spread("Then I saw my old teacher there at the big market", 2.5, 4.5, "S1")
    cues = build_cues([*first, *reply, *then], cuts=[], rules=rules)
    shown = holding(cues, "Really?")
    assert shown.start >= 2.0 and "today." not in [w.text for w in shown.words]
    assert holding(cues, "today.").end <= 2.3


def test_a_reply_no_subtitle_holds_gets_its_own_and_stretches_none() -> None:
    first = spread("I went to the market today.", 0.0, 2.0, "S1")
    cue = Cue(0.0, first[-1].end, list(first), parts=[list(first)])
    reply = spread("Really?", 2.3, 2.8, "S2")
    placed = take_reply([cue], reply, DEFAULT_RULES)
    assert len(placed) == 2 and placed[0].end == first[-1].end
    assert parts_of(placed[1]) == [["Really?"]]


def test_a_reply_said_just_before_a_turn_is_its_first_part() -> None:
    then = spread("Then I saw my old teacher there", 2.5, 4.5, "S1")
    cue = Cue(2.5, then[-1].end, list(then), parts=[list(then)])
    reply = spread("Really?", 2.3, 2.8, "S2")
    [host] = with_replies([cue], [reply], DEFAULT_RULES)
    assert parts_of(host)[0] == ["Really?"] and host.start == 2.3


@pytest.mark.parametrize("rules", [DEFAULT_RULES, fitted(DEFAULT_RULES, 1080, 1920)])
def test_the_same_speakers_words_joined_onto_an_exchange_still_fit_one_line(
        rules: Rules) -> None:
    words = [*spread("Really?", 0.0, 0.5, "S1"), *spread("Yes.", 0.6, 0.8, "S2"),
             *spread("I went there with my brother and we saw it all", 0.9, 5.0, "S2")]
    for cue in build_cues(words, cuts=[], rules=rules):
        if cue.is_dialogue:
            assert all(len(" ".join(part)) <= rules.part_chars for part in parts_of(cue))


def test_a_reply_longer_than_a_line_starts_a_subtitle_but_shares_it_with_nobody() -> None:
    rules = fitted(DEFAULT_RULES, 1080, 1920)
    turn = spread("one two three four five six", 0.0, 3.0, "S1")
    host = Cue(0.0, 3.0, list(turn), parts=[list(turn)])
    reply = spread("Really? You went there alone?", 0.6, 1.6, "S3")
    assert len(" ".join(w.text for w in reply)) > rules.part_chars
    assert all(not c.is_dialogue for c in split_at(host, reply, rules))


def test_an_unlabelled_reply_part_is_never_glued_to_the_next_subtitles_words() -> None:
    words = [Word("we", 0.0, 0.25), Word("went", 0.25, 0.6), Word("there.", 0.6, 0.95),
             Word("yeah", 0.7, 1.1), Word("and", 0.95, 1.3), Word("then", 1.3, 1.5),
             Word("we", 1.5, 1.6), Word("left", 1.6, 1.9)]
    for cue in build_cues(words, cuts=[]):
        for part in parts_of(cue):
            assert "yeah" not in part or part == ["yeah"]


def test_a_labelled_reply_part_keeps_its_own_line_when_subtitles_join() -> None:
    turn = spread("we went there.", 0.0, 0.9, "S1")
    reply = spread("yeah", 0.5, 0.9, "S2")
    later = spread("yes we did", 0.95, 1.3, "S2")
    host = Cue(0.0, 0.9, list(turn), parts=[list(turn)])
    following = Cue(0.95, 1.3, list(later), parts=[list(later)])
    cues = fit_timing(with_replies([host, following], [reply], DEFAULT_RULES), DEFAULT_RULES)
    assert all(part != ["yeah", "yes", "we", "did"] for c in cues for part in parts_of(c))


def test_the_srt_breaks_lines_as_the_portrait_picture_does(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    text = "رحت السوق اليوم وشفت أستاذي القديم هناك"
    cues = [Cue(0.0, 3.0, [Word("I", 0.0, 0.5)], text=text)]
    monkeypatch.setattr(pipeline, "placed", lambda _j, _c, canvas, _d: canvas)
    job = Job(tmp_path / "v.mp4", burn=False, out_dir=tmp_path, cache_dir=tmp_path / "cache")
    rules = fitted(job.rules, 1080, 1920)
    expected = display_lines(text, rules)
    assert len(expected) == 2
    for made in (pipeline.Made(cues, [], media.VideoInfo(1080, 1920, 9.0)),
                 pipeline.Made(cues, [], media.VideoInfo(1080, 1920, 9.0), rules)):
        pipeline.write_outputs(job, made, pipeline.quiet)
        srt = job.output(".srt").read_text(encoding="utf-8-sig")
        assert all(line in srt for line in expected)


@pytest.mark.parametrize("text", [
    "ฉันไปตลาดเมื่อวานนี้และได้เจอครูเก่า",
    "เมื่อวานนี้ฉันไปเที่ยวทะเลกับครอบครัวที่น่ารัก",
    "น้ำน้ำน้ำน้ำน้ำน้ำน้ำน้ำน้ำน้ำน้ำน้ำน้ำน้ำ"])
def test_a_thai_line_never_starts_with_a_mark_of_the_letter_before_it(text: str) -> None:
    rules = rules_for(language("th"))
    lines = balance_lines(text, rules)
    assert "".join(lines) == text
    for line in lines[1:]:
        assert unicodedata.category(line[0]) not in {"Mn", "Mc", "Me"}
        assert line[0] != "ำ"
    for line in lines[:-1]:
        assert not "เ" <= line[-1] <= "ไ"
