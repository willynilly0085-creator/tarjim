"""Each translation setting changes its own line of the prompt, and nothing else; with nothing
changed the prompt is word for word the one asked before the settings (2026-11-09)."""
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from tarjim import pipeline
from tarjim.job import Job
from tarjim.languages import language
from tarjim.models import Cue, Word
from tarjim.prefs.active import using
from tarjim.prefs.model import resolve
from tarjim.translate import prompt
from tarjim.translate.prompt import Brief, build_prompt

CUES = [Cue(0.0, 2.0, [Word("Three", 0.0, 0.5), Word("months", 0.5, 1.0)])]
BEFORE_AR = ("- أي عدد من 3 وفوق يُكتب بالأرقام اللاتينية 0-9 حتى لو نُطق كلمة (three months ← 3 "
             "شهور، 18 times ← 18 مرة)؛ أما مرة ومرتين فتبقى كلمات. بدون علامتي ؟ و ! مع بعض.\n"
             "- لو الخانة مجرد صوت بلا معنى، أرجع نصاً فارغاً.")
FILLERS_AR = "— اختصر واحذف الحشو مثل um و like و you know، مثل الترجمة الاحترافية. الـ budget"
BEFORE_ANY = ("condense and drop fillers such as um, like and you know, the way professional "
              "subtitlers do. A budget written a+b is a limit for each part of an exchange")


def asked(code: str = "ar", **values: Any) -> list[str]:
    manner = resolve({f"translate.{k}": v for k, v in values.items()}, {}, code).translate
    brief = Brief(language(code), rules=Brief().rules, manner=manner)
    return build_prompt(CUES, brief).splitlines()


def changed(code: str = "ar", **values: Any) -> tuple[list[str], list[str]]:
    before, after = asked(code), asked(code, **values)
    return [old for old in before if old not in after], [new for new in after if new not in before]


def test_nothing_changed_asks_as_before() -> None:
    text = "\n".join(asked())
    assert BEFORE_AR in text and FILLERS_AR in text
    assert BEFORE_ANY in "\n".join(asked("en"))
    assert build_prompt(CUES, Brief()) == "\n".join(asked()) == build_prompt(
        CUES, replace(Brief(), manner=prompt.USUAL))


@pytest.mark.parametrize(("values", "gone", "added"), [
    ({"numbers": "eastern"}, 1, 1), ({"numbers": "words"}, 1, 1),
    ({"question_marks": "keep"}, 1, 1), ({"fillers": "keep"}, 1, 1),
    ({"register": "casual"}, 0, 1), ({"register": "formal"}, 0, 1),
    ({"profanity": "soften"}, 0, 1), ({"profanity": "mask"}, 0, 1),
    ({"names": "latin"}, 0, 1), ({"names": "target"}, 0, 1),
])
def test_each_choice_replaces_or_adds_its_own_line(values: dict[str, Any], gone: int,
                                                    added: int) -> None:
    for code in ("ar", "en"):
        before, after = changed(code, **values)
        # the English prompt never had a rule for ؟!, and Arabic digits are Arabic's alone
        if code == "en" and values in ({"question_marks": "keep"}, {"numbers": "eastern"}):
            assert (before, after) == ([], [])
            continue
        assert (len(before), len(after)) == (gone, added), (code, values)


def test_eastern_digits_and_kept_question_marks_say_so() -> None:
    _gone, eastern = changed(numbers="eastern")
    assert "٠-٩" in eastern[0] and "؟" in eastern[0]
    _gone, kept = changed(question_marks="keep")
    assert "؟" not in kept[0] and "0-9" in kept[0]


def test_eastern_digits_are_for_arabic_only() -> None:
    assert resolve({"translate.numbers": "eastern"}, {}, "fa").translate.numbers == "latin"
    assert resolve({"translate.numbers": "eastern"}, {}, "ar").translate.numbers == "eastern"


def test_the_job_asks_with_its_own_manner(tmp_path: Path,
                                          monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Brief] = []

    class Rounds:
        def __init__(self, _cues: list[Cue], _audio: Any, brief: Brief) -> None:
            seen.append(brief)
            self.stopped: list[Exception] = []

        def run(self) -> list[Exception]:
            return []

        def finish(self, _rules: Any) -> None:
            return None

    from tarjim.translate import rounds

    monkeypatch.setattr(rounds, "Rounds", Rounds)
    job = Job(tmp_path / "v.mp4", cache_dir=tmp_path)
    with using(resolve({"translate.register": "formal"}, {}, "ar")):
        pipeline.translate(job, list(CUES))
    assert seen[0].manner.register == "formal"


def test_without_the_local_backup_only_the_chosen_engine_translates(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from tarjim.engines import choice
    from tarjim.rules import DEFAULT_RULES
    from tests.test_translate_resilience import Answers, said

    job: Any = type("Job", (), {"language": language("fr"), "dialect": "", "target": "fr",
                                "rules": DEFAULT_RULES, "video": tmp_path / "v.mp4"})()
    chosen = Answers([{"id": 1, "text": "Bonjour."}], RuntimeError("503"), RuntimeError("503"))
    backup = Answers([{"id": 1, "text": "Au revoir."}])
    monkeypatch.setattr(choice, "chain", lambda _task: ["gemini", "local"])
    monkeypatch.setattr(choice, "asker", {"gemini": chosen, "local": backup}.__getitem__)
    with using(resolve({"translate.local_backup": False}, {}, "fr")):
        done = pipeline.translate(job, [said(0, "Hello."), said(400, "Bye.")])
    assert done[0].text == "Bonjour." and backup.prompts == []
