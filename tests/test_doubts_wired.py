"""The witnesses and the doubts reach a real job: the timing step writes who wrote each word, a
kept transcript keeps it, and the job's record gets the lines to look at (2026-11-14)."""
import json
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
import soundfile

from tarjim import hearing, pipeline
from tarjim.asr.base import Transcript
from tarjim.findings import FINDINGS, Findings
from tarjim.job import Job
from tarjim.listen import check, clipmap, kept, settle, timing
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Fill, Heard
from tarjim.listen.witness import alone
from tarjim.models import Cue, Word
from tarjim.prefs.active import using
from tarjim.prefs.model import resolve

HEARD = Utterance(0.0, 2.0, "S1", "we met Staley")
MISHEARD = Utterance(0.0, 2.0, "S1", "we met daily")
ASKED_AGAIN = Utterance(5.0, 6.0, "S1", "and left")
OWN = Utterance(8.0, 9.0, "S1", "then nothing", request="local")


def words_of(*lines: Utterance) -> list[Word]:
    return [Word(text, line.start + k * 0.3, line.start + k * 0.3 + 0.2, "S1")
            for line in lines for k, text in enumerate(line.text.split())]


@pytest.fixture
def found() -> Iterator[Findings]:
    record = Findings()
    token = FINDINGS.set(record)
    yield record
    FINDINGS.reset(token)


@pytest.mark.usefixtures("found")
def test_the_timing_step_writes_who_wrote_each_word(tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    audio = tmp_path / "a.wav"
    soundfile.write(audio, np.zeros(8000, dtype=np.float32), 8000)
    done = settle.Timed(Transcript("English", "", words_of(HEARD, ASKED_AGAIN, OWN)), True, 0.9,
                        fills=[Fill(ASKED_AGAIN, (5.0, 6.0)), Fill(OWN, (8.0, 9.0))])
    monkeypatch.setattr(settle, "settled", lambda *_args: done)
    monkeypatch.setattr(check, "regions_in", lambda _wav: [])
    monkeypatch.setattr(clipmap, "letters_of", lambda _wav: None)
    monkeypatch.setattr(hearing, "second_opinion", lambda *_args: [])
    monkeypatch.setattr(timing, "final_scores", lambda _wav, words: words)
    heard = Heard("English", [HEARD], [[HEARD], [MISHEARD], [MISHEARD]], provider="gemini")
    with using(resolve({"listen.voice_check": False}, {}, "ar")):
        transcript, _whole = hearing.listen_and_align(Job(tmp_path / "v.mp4"), audio, heard,
                                                      lambda _stage: None)
    assert [w.backed for w in transcript.words] == [3, 3, 1, 1, 1, 0, 0]
    assert [alone(w) for w in transcript.words] == [False, False, True, True, True, True, True]


def test_a_kept_transcript_keeps_who_wrote_each_word(tmp_path: Path) -> None:
    words = [Word("Staley", 0.0, 0.4, "S1", backed=1, local=False), Word("left", 0.5, 0.9, "S1")]
    kept.keep_transcript(tmp_path, Transcript("English", "Staley left", words))
    back = kept.kept_transcript(tmp_path)
    assert back is not None
    assert [(w.backed, w.local) for w in back[0].words] == [(1, False), (None, None)]


def test_a_job_keeps_the_lines_it_is_not_sure_of(tmp_path: Path, found: Findings) -> None:
    said = [Word("we", 0.0, 0.3, "S1", backed=3), Word("met", 0.3, 0.6, "S1", backed=3),
            Word("Staley", 0.6, 1.0, "S1", backed=1)]
    job = Job(tmp_path / "v.mp4", cache_dir=tmp_path / "cache")
    pipeline.save_review(job, [Cue(0.0, 1.4, said, "قابلنا ستيلي")])
    assert found.doubts is not None and found.doubts.hearing == (1,)
    rows = json.loads((job.cache / "cues.ar.json").read_text(encoding="utf-8"))
    assert rows[0]["doubts"] == ["hearing"] and rows[0]["text"] == "قابلنا ستيلي"
    notes = found.notes([Cue(0.0, 1.4, said, "قابلنا ستيلي")], [])
    assert [note["kind"] for note in notes] == ["hearing_doubt"]
