"""A finished job keeps what it knows is not right: the checks of its subtitles, speech left
without words, lines no engine translated and a timing found off the voice. The page shows it
as done with notes, in every language of the page, instead of plain success."""
import json
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import soundfile

import tarjim.pipeline
from tarjim import hearing
from tarjim.asr.base import Transcript
from tarjim.findings import FINDINGS, Findings, findings
from tarjim.job import Job
from tarjim.listen import check, clipmap, settle
from tarjim.listen.coverage import Gap
from tarjim.listen.merge import Heard
from tarjim.models import Cue, Word
from tarjim.qa import Issue
from tarjim.server import engine, job_record
from tarjim.server.jobs import Board, Order, Task
from tarjim.ui_languages import FOLDER

WEB = Path(__file__).resolve().parents[1] / "tarjim" / "web"
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
KINDS = ("speech_left", "in_source", "untranslated", "overlap", "readability", "timing",
         "sounds", "engine_stopped", "budget_used", "hearing_doubt", "hearing_unchecked",
         "meaning_doubt", "timing_doubt")
UNCOUNTED = ("timing", "engine_stopped", "hearing_unchecked")  # said once, with no "how many"


@pytest.fixture
def found() -> Iterator[Findings]:
    """The job's record, put back as it was after the test."""
    record = Findings()
    token = FINDINGS.set(record)
    yield record
    FINDINGS.reset(token)


def lines() -> list[Cue]:
    return [Cue(t * 10.0, t * 10.0 + 2, [Word(f"w{t}", t * 10.0, t * 10.0 + 2)]) for t in range(4)]


def test_the_notes_list_each_kind_with_where_it_is() -> None:
    found = Findings(left=[(61.0, 64.0)], agreement=0.31, in_source=[2], sounds=[4],
                     over_budget=[1])
    issues = [Issue(4, "untranslated", "Mm."), Issue(3, "untranslated", "w2"),
              Issue(1, "reading_speed", "30 cps"), Issue(3, "overlap", "ends 22.10")]
    notes = {note["kind"]: note for note in found.notes(lines(), issues)}
    assert notes["speech_left"]["at"] == [61.0] and notes["in_source"]["at"] == [10.0]
    assert notes["untranslated"]["count"] == 1 and notes["overlap"]["at"] == [20.0]
    assert notes["readability"] == {"kind": "readability", "problem": False, "count": 1,
                                    "at": [0.0]}
    assert notes["sounds"] == {"kind": "sounds", "problem": False, "count": 1, "at": [30.0]}
    assert notes["timing"]["share"] == 31 and all(n["problem"] for k, n in notes.items()
                                                  if k not in ("readability", "sounds"))


def test_a_clean_job_has_no_notes() -> None:
    assert Findings(agreement=0.97).notes(lines(), []) == []
    assert Findings().notes(lines(), [Issue(1, "untranslated", "Mm.")]) != []


@pytest.mark.usefixtures("found")
def test_the_server_keeps_the_notes_and_the_list_keeps_them_over_a_restart(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(engine, "HOME", tmp_path / "home")
    (tmp_path / "talk.mp4").write_bytes(b"video")

    def run(_job: Job, _report: Any) -> tuple[list[Cue], list[Issue]]:
        findings().heard(((30.0, 33.0),), 0.95)
        findings().in_source.append(1)
        return lines(), [Issue(2, "overlap", "ends 12.00")]

    monkeypatch.setattr(tarjim.pipeline, "run", run)
    task = Task(Order(str(tmp_path / "talk.mp4")))
    engine.perform(task, tmp_path / "out")
    assert [n["kind"] for n in task.notes] == ["speech_left", "in_source", "overlap"]
    assert task.view()["notes"] == task.notes
    monkeypatch.setattr("tarjim.server.jobs.watch", lambda: None)
    board = Board(lambda _task: None)
    task.stage = "done"
    board.tasks[task.id] = task
    job_record.write_down(board, tmp_path)
    again = Board(lambda _task: None)
    job_record.restore(again, tmp_path)
    assert again.tasks[task.id].notes == task.notes


def test_a_list_written_before_notes_still_loads(tmp_path: Path,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tarjim.server.jobs.watch", lambda: None)
    row = {"id": "old", "error": "", "error_code": "", "failed_at": "", "created": 1.0,
           "stage": "done", "order": {"source": "a.mp4"}, "video": "", "outputs": []}
    (tmp_path / job_record.JOBS).write_text(json.dumps([row]), encoding="utf-8")
    board = Board(lambda _task: None)
    job_record.restore(board, tmp_path)
    assert board.tasks["old"].notes == [] and board.tasks["old"].stage == "done"


def test_hearing_writes_down_the_speech_left_and_the_timing_check(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, found: Findings) -> None:
    audio = tmp_path / "a.wav"
    soundfile.write(audio, np.zeros(8000, dtype=np.float32), 8000)
    done = settle.Timed(Transcript("English", "hi"), False, 0.4, left=[Gap(12.0, 15.0, 3.0, [])])
    monkeypatch.setattr(settle, "settled", lambda *_args: done)
    monkeypatch.setattr(check, "regions_in", lambda _wav: [])
    # no aligner is loaded for the speech map (2026-11-09): its letters are not heard here
    monkeypatch.setattr(clipmap, "letters_of", lambda _wav: None)
    heard = Heard("English", [], [], local_words=[])
    hearing.listen_and_align(Job(tmp_path / "v.mp4"), audio, heard, lambda _stage: None)
    assert found.left == [(12.0, 15.0)] and found.agreement == 0.4


@pytest.mark.parametrize("path", sorted(FOLDER.glob("*.json")), ids=lambda p: p.stem)
def test_every_page_language_words_the_notes_without_emoji(path: Path) -> None:
    words = json.loads(path.read_text(encoding="utf-8"))
    keys = ["stage_doneNotes", *(f"note_{kind}" for kind in KINDS)]
    assert all(words.get(key, "").strip() for key in keys)
    assert not [key for key in keys if EMOJI.search(words[key])]
    counted = [kind for kind in KINDS if kind not in UNCOUNTED]
    assert all("{n}" in words[f"note_{kind}"] for kind in counted)
    assert "{share}" in words["note_timing"] and "{reason}" in words["note_engine_stopped"]


def test_the_page_shows_a_job_with_problems_as_done_with_notes() -> None:
    page = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "notes.js").read_text(encoding="utf-8")
    jobs = (WEB / "jobs.js").read_text(encoding="utf-8")
    assert 'class="job-notes"' in page and "stage_doneNotes" in script
    assert "note.problem" in script and "showNotes(" in jobs
    ar = json.loads((FOLDER / "ar.json").read_text(encoding="utf-8"))
    assert ar["stage_doneNotes"] == "خلص، وفيه ملاحظات"


NOTES_CHECK = """
const { readFileSync } = await import("node:fs");
const [notesUrl, i18nUrl, wordsPath] = process.argv.slice(1);
globalThis.document = { documentElement: { lang: "", dir: "" }, querySelectorAll: () => [],
  createElement: (tag) => ({ tag }) };
globalThis.fetch = async () => ({ json: async () => JSON.parse(readFileSync(wordsPath, "utf8")) });
await (await import(i18nUrl)).load("ar");
const notes = await import(notesUrl);
const stopped = { kind: "engine_stopped", problem: true, count: 1, at: [], reason: "quota",
  detail: "quota used up" };
const quiet = { kind: "readability", problem: false, count: 2, at: [61, 125.4] };
const list = { dataset: {}, hidden: true, items: [],
  replaceChildren(...items) { this.items = items; } };
const row = { dataset: {}, querySelector: () => list };
const done = { stage: "done", notes: [stopped, quiet] };
notes.showNotes(row, done);
const shown = { flag: row.dataset.notes, hidden: list.hidden,
  items: list.items.map((li) => [li.className, li.textContent]) };
notes.showNotes(row, { stage: "translating", notes: [stopped] });
console.log(JSON.stringify({ ...shown, label: notes.stageLabel(done),
  quiet: notes.stageLabel({ stage: "done", notes: [quiet] }),
  running: notes.stageLabel({ stage: "translating", notes: [stopped] }),
  paused: notes.stageLabel({ stage: "done", paused: true, notes: [stopped] }),
  afterwards: [row.dataset.notes, list.hidden] }));
"""


@pytest.mark.skipif(not shutil.which("node"), reason="needs node")
def test_the_page_script_lists_the_notes_and_says_done_with_notes() -> None:
    """The page itself, run: a stopped engine says why in the failed-job words, a readability
    warning alone stays plain done, and a job still running shows no notes."""
    args = [str(shutil.which("node")), "--input-type=module", "-e", NOTES_CHECK,
            (WEB / "notes.js").as_uri(), (WEB / "i18n.js").as_uri(), str(FOLDER / "ar.json")]
    seen = json.loads(subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                                     check=True, timeout=60).stdout)
    ar = json.loads((FOLDER / "ar.json").read_text(encoding="utf-8"))
    why = ar["note_engine_stopped"].replace("{reason}", ar["err_quota"])
    assert seen["items"][0] == ["", f"{why}\n" + ar["errorDetail"].replace("{detail}",
                                                                           "quota used up")]
    assert seen["items"][1][0] == "note-quiet" and "1:01" in seen["items"][1][1]
    assert "2:05" in seen["items"][1][1]
    assert seen["label"] == "خلص، وفيه ملاحظات" and seen["quiet"] == ar["stage_done"]
    assert seen["running"] == ar["stage_translating"] and seen["paused"] == ar["stage_paused"]
    assert seen["flag"] == "true" and seen["hidden"] is False
    assert seen["afterwards"] == ["false", True]
