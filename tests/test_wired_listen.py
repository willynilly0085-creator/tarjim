"""Each listening setting changes how a clip is heard, and a kept hearing or transcript made
with other settings is not served as if made with these (2026-11-09)."""
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import soundfile

from tarjim import hearing, media
from tarjim.asr.base import Transcript
from tarjim.engines import choice
from tarjim.job import Job
from tarjim.listen import check, chunks, coverage, kept, opinion, settle, whose
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.heard_align import listen_and_align
from tarjim.listen.merge import Heard, listen_many
from tarjim.models import Word
from tarjim.prefs.active import plain, using
from tarjim.prefs.model import Prefs, resolve

SAID = [Utterance(0.0, 1.0, "S1", "Hello there")]


def prefs(**values: Any) -> Prefs:
    return resolve({f"listen.{k}": v for k, v in values.items()}, {}, "ar")


@pytest.mark.parametrize("passes", [1, 3, 5])
def test_a_clip_is_heard_in_as_many_passes_as_the_person_chose(passes: int) -> None:
    asked: list[int] = []

    def listen() -> tuple[str, list[Utterance]]:
        asked.append(1)
        return "en", SAID

    with using(prefs(passes=passes)):
        heard = listen_many(listen)
    assert len(asked) == passes == len(heard.passes) and heard.utterances == SAID


def test_pieces_and_gaps_follow_the_settings_and_the_old_names_still_win(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TARJIM_LISTEN_CHUNK_SECONDS", raising=False)
    monkeypatch.delenv("TARJIM_COVERAGE_GAP_SECONDS", raising=False)
    assert (chunks.chunk_seconds(), coverage.gap_seconds()) == (75.0, 2.0)
    with using(prefs(chunk_seconds=45, gap_seconds=1.5)):
        assert (chunks.chunk_seconds(), coverage.gap_seconds()) == (45.0, 1.5)
        monkeypatch.setenv("TARJIM_LISTEN_CHUNK_SECONDS", "0")
        assert chunks.chunk_seconds() == 0.0


def test_the_backup_engine_is_left_out_when_the_person_turned_it_off(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(choice, "chain", lambda _role: ["gemini", "local"])
    assert choice.tried("listen", True) == ["gemini", "local"]
    assert choice.tried("translate", False) == ["gemini"]


def silent_job(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Job:
    import tarjim.memory

    def extract(_video: Path, target: Path) -> Path:
        soundfile.write(target, np.zeros(16000, dtype=np.float32), 16000)
        return target

    monkeypatch.setattr(tarjim.memory, "free_for_listening", lambda: None)
    monkeypatch.setattr(media, "extract_audio", extract)
    return Job(tmp_path / "v.mp4", cache_dir=tmp_path / "cache")


@pytest.mark.parametrize("heard", [RuntimeError("gemini 503"),
                                   Heard("en", [], [], provider="gemini")])
def test_without_the_local_backup_a_job_fails_instead_of_ending_empty(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch, heard: Any) -> None:
    job, stood_in = silent_job(tmp_path, monkeypatch), []

    def listen(_video: Path, _audio: Path) -> Heard:
        if isinstance(heard, Exception):
            raise heard
        return heard

    monkeypatch.setattr(hearing, "listen_video", listen)
    monkeypatch.setattr(hearing, "qwen_transcript", lambda _a: stood_in.append(1) or Transcript(
        language="en", text="hi", words=[Word("hi", 0.1, 0.4)]))
    assert hearing.transcript_for(job, lambda _s: None).text == "hi" and stood_in == [1]
    with using(prefs(local_backup=False)), pytest.raises(RuntimeError, match=r"503|turned off"):
        hearing.transcript_for(job, lambda _s: None)
    assert stood_in == [1]


def test_a_kept_hearing_asked_in_other_passes_is_heard_again(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job, listened = silent_job(tmp_path, monkeypatch), []
    kept.keep_heard(job.cache, Heard("en", SAID, [SAID], provider="gemini", asked=3))

    def listen(_video: Path, _audio: Path) -> Heard:
        listened.append(1)
        return Heard("en", SAID, [SAID], provider="gemini", asked=5)

    monkeypatch.setattr(hearing, "listen_video", listen)
    audio = tmp_path / "a.wav"
    assert hearing.heard_for(job, audio).asked == 3 and listened == []
    with using(prefs(passes=5)):
        assert hearing.heard_for(job, audio).asked == 5 and listened == [1]


def test_a_hearing_kept_before_the_settings_is_reused_as_it_was(tmp_path: Path) -> None:
    for provider, asked in (("gemini", 3), ("openai", 1), ("", 3)):
        kept.keep_heard(tmp_path, Heard("en", SAID, [SAID], provider=provider))
        path = tmp_path / kept.HEARD
        path.write_text(path.read_text(encoding="utf-8").replace('"asked"', '"was"'),
                        encoding="utf-8")
        found = kept.load_heard(tmp_path)
        assert found is not None and found.asked == asked == hearing.asked_for(provider)


def test_the_transcripts_key_names_each_changed_listening_setting_only() -> None:
    usual = kept.derive_key()
    with using(plain()):
        assert kept.derive_key() == usual
    keys = set()
    for chosen in (prefs(passes=5), prefs(second_opinion=False), prefs(voice_check=False),
                   prefs(chunk_seconds=60), prefs(gap_seconds=1.5), prefs(aligner="tolerant")):
        with using(chosen):
            keys.add(kept.derive_key())
    assert usual not in keys and len(keys) == 6


def aligned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, chosen: Prefs) -> list[str]:
    asked: list[str] = []
    audio = tmp_path / "a.wav"
    soundfile.write(audio, np.zeros(16000, dtype=np.float32), 16000)
    words = [Word("Hello", 0.1, 0.4, "S1")]
    done = settle.Timed(Transcript(language="en", text="Hello", words=words), True, 1.0)

    def opinion_of(_audio: Path, _language: str = "") -> list[Word]:
        asked.append("second opinion")
        return []

    def voices(found: list[Word], _wav: Any, _rate: int = 16000) -> list[Word]:
        asked.append("voice")
        return found

    monkeypatch.setattr(hearing, "second_opinion", opinion_of)
    monkeypatch.setattr(whose, "by_voice", voices)
    monkeypatch.setattr(settle, "settled", lambda *_a: done)
    monkeypatch.setattr(check, "regions_in", lambda _wav: [])
    monkeypatch.setattr(opinion, "sounded", lambda found, _wav: found)
    with using(chosen):
        listen_and_align(Job(tmp_path / "v.mp4", cache_dir=tmp_path), audio,
                         Heard("en", SAID, [SAID], provider="gemini"), lambda _s: None)
    return asked


def test_the_speed_switches_skip_the_second_opinion_and_the_voice_check(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert aligned(tmp_path, monkeypatch, prefs()) == ["second opinion", "voice"]
    assert aligned(tmp_path, monkeypatch, prefs(second_opinion=False)) == ["voice"]
    assert aligned(tmp_path, monkeypatch, prefs(voice_check=False)) == ["second opinion"]
