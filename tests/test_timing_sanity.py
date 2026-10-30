"""A timing no one could speak never reaches the subtitles (2026-10-30: 378 words in 5 seconds)."""
from pathlib import Path

from tarjim import hearing
from tarjim.asr.base import Transcript
from tarjim.asr.sanity import implausible, plausible_line
from tarjim.job import Job
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import agreed, sane
from tarjim.models import Word

SPEECH = " ".join(f"word{k}" for k in range(300))


def spoken(count: int, start: float, step: float) -> list[Word]:
    return [Word(f"w{k}", start + k * step, start + k * step + step * 0.8) for k in range(count)]


def test_words_squeezed_into_seconds_are_caught_and_real_speech_is_not() -> None:
    assert implausible(spoken(378, 65.6, 5.4 / 378))
    assert not implausible(spoken(378, 0.0, 128.0 / 378))
    assert not implausible(spoken(5, 0.0, 0.01))  # too few words to tell


def test_a_pass_with_the_whole_speech_in_one_line_is_left_out_of_the_vote() -> None:
    lines = [Utterance(k * 4.0, k * 4.0 + 3.5, "S1", " ".join(SPEECH.split()[k * 10:k * 10 + 10]))
             for k in range(30)]
    whole = [Utterance(0.0, 129.1, "S1", SPEECH)]
    assert not sane(whole) and sane(lines)
    assert agreed([whole, lines, lines]) == agreed([lines, lines])
    assert not plausible_line(0.0, 5.0, SPEECH)


def test_a_broken_timing_kept_by_an_older_run_is_made_again(tmp_path: Path,
                                                            monkeypatch) -> None:  # type: ignore[no-untyped-def]
    job = Job(tmp_path / "v.mp4", cache_dir=tmp_path)
    Transcript("English", "x", spoken(378, 65.6, 5.4 / 378)).save(job.cache / "transcript.json")
    fresh = Transcript("English", "x", spoken(378, 0.0, 0.33))
    monkeypatch.setattr(hearing, "hear", lambda *_a: (fresh, True))
    monkeypatch.setattr(hearing.media, "extract_audio", lambda *_a: None)
    monkeypatch.setattr("tarjim.memory.free_for_listening", lambda: None)
    assert hearing.transcript_for(job).words[0].start == 0.0
