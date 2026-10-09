"""Failures that used to end a job quietly, or with the wrong reason."""
import json
from pathlib import Path
from typing import Any

import pytest

from tarjim import hearing, pipeline
from tarjim.asr.align import GAP_FALLBACK, Slot, fill_gaps
from tarjim.dialogue import Piece
from tarjim.dub import script
from tarjim.dub.lines import Line
from tarjim.engines import choice, web
from tarjim.languages import language
from tarjim.lines import display_lines
from tarjim.models import Cue, Word
from tarjim.qa import check
from tarjim.render import burn as burning
from tarjim.rules import DEFAULT_RULES
from tarjim.segment import split_long
from tarjim.translate.gemini import Translator
from tarjim.translate.prompt import Brief


class Answers:
    hears = False

    def __init__(self, *answers: Any) -> None:
        self.answers = list(answers)

    def ask(self, _prompt: str, _audio: bytes | None, _schema: dict[str, Any]) -> Any:
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def cues() -> list[Cue]:
    return [Cue(0.0, 1.0, [Word("Hello.", 0.0, 1.0)]), Cue(2.0, 3.0, [Word("Bye.", 2.0, 3.0)])]


def brief() -> Brief:
    return Brief(language("fr"), "", DEFAULT_RULES)


def silence(_start: float, _end: float) -> bytes:
    return b""


def test_a_hyphen_inside_a_word_survives_in_dialogue() -> None:
    assert display_lines("Est-ce que tu viens ? || - Peut-être") == [
        "- Est-ce que tu viens ?", "- Peut-être"]


def test_a_title_with_an_apostrophe_is_burned(tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    folder = tmp_path / "it's here"
    folder.mkdir()
    ass, target = folder / "Don't stop.ar.ass", folder / "Don't stop.ar.mp4"
    ass.write_text("[Script Info]", encoding="utf-8")
    seen: list[str] = []

    def fake_run(args: list[str], cwd: Path | None = None) -> Any:
        graph = args[args.index("-vf") + 1]
        name = graph.removeprefix("ass=")
        seen.append(graph)
        assert cwd is not None and (cwd / name).read_text(encoding="utf-8") == "[Script Info]"
        target.write_bytes(b"video")
        return type("Done", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(burning, "run", fake_run)
    monkeypatch.setattr(burning, "tool", lambda name: name)
    assert burning.burn(folder / "Don't stop.mp4", ass, target) == target
    assert seen and all(mark not in seen[0] for mark in "'\\:")


@pytest.mark.parametrize("answer", [None, [], [{"id": 9, "text": "x"}]])
def test_a_reply_that_translates_nothing_is_a_failure(answer: Any) -> None:
    with pytest.raises(RuntimeError, match="empty"):
        Translator(Answers(answer, answer)).translate(cues(), silence, brief())  # type: ignore[arg-type]


def test_line_numbers_written_as_text_are_still_understood() -> None:
    answer = [{"id": "1", "text": "Bonjour."}, {"id": 2.0, "text": "Salut."}]
    done = Translator(Answers(answer)).translate(cues(), silence, brief())  # type: ignore[arg-type]
    assert [c.text for c in done] == ["Bonjour.", "Salut."]


def test_a_line_left_without_translation_is_reported() -> None:
    some = cues()
    some[0].text = "Bonjour."
    assert [(i.number, i.kind) for i in check(some)] == [(2, "untranslated")]


def test_a_reply_that_is_not_json_is_an_engine_error() -> None:
    with pytest.raises(web.EngineError):
        web.parse_json("Sure! Here is the JSON: {")


def test_the_chosen_engine_names_the_failure_and_a_bad_reply_moves_on(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    job: Any = type("Job", (), {"language": language("fr"), "dialect": "", "target": "fr",
                                "rules": DEFAULT_RULES, "video": tmp_path / "v.mp4"})()
    monkeypatch.setattr(choice, "chain", lambda _task: ["claude", "local"])
    askers = {"claude": Answers(RuntimeError("claude: sign in again")),
              "local": Answers(KeyError("choices"))}
    monkeypatch.setattr(choice, "asker", lambda provider: askers[provider])
    with pytest.raises(RuntimeError, match="sign in again"):
        pipeline.translate(job, cues())
    good = [{"id": 1, "text": "Bonjour."}, {"id": 2, "text": "Salut."}]
    askers.update(claude=Answers(json.JSONDecodeError("bad", "", 0)), local=Answers(good))
    assert [c.text for c in pipeline.translate(job, cues())] == ["Bonjour.", "Salut."]


def test_a_missing_second_listener_does_not_stop_the_job(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(_audio: Path) -> Any:
        raise OSError("Qwen/Qwen3-ASR is not a local folder")

    monkeypatch.setattr(hearing, "qwen_transcript", missing)
    assert hearing.second_opinion(Path("a.wav")) == []
    with pytest.raises(RuntimeError, match="local listener"):
        hearing.local_transcript(Path("a.wav"))


def test_a_number_at_the_start_is_placed_just_before_the_next_word() -> None:
    slots = [Slot("3", "S1", 0), Slot("things", "S1", 0, 20.0, 20.4, True)]
    fill_gaps(slots)
    assert (slots[0].start, slots[0].end) == (20.0 - GAP_FALLBACK, 20.0)


def test_splitting_a_long_block_keeps_that_it_follows_a_cut() -> None:
    words = [Word(f"w{n}", float(n), n + 0.9) for n in range(40)]
    pieces = split_long(Piece(words, new_speaker=True, after_cut=True), DEFAULT_RULES)
    assert len(pieces) > 1 and pieces[0].after_cut and not pieces[1].after_cut


def test_a_script_numbered_from_zero_is_refused_not_crashed(
        monkeypatch: pytest.MonkeyPatch) -> None:
    lines = [Line(0.0, 1.0, "S1", "مرحبا", "hi"), Line(1.0, 2.0, "S1", "وداعا", "bye")]
    wrong = [{"id": 0, "say": "مرحبا"}, {"id": 1, "say": "وداعا"}]
    monkeypatch.setattr(script, "chain", lambda _task: ["claude"])
    monkeypatch.setattr(script, "asker", lambda _provider: Answers(wrong))
    assert script.spoken_lines(lines, "Arabic", "saudi") is None
