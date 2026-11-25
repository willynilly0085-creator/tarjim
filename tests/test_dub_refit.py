"""2026-11-25: in the owner's clip of Mark and Joanna Stern, "لأن الكثير من الناس يريدون التحدث
إليه" had 1.1 s and was said in about 2 s: sped up 1.8 times, then its end cut off."""
from pathlib import Path

import numpy as np
import pytest

from tarjim.dub import refit
from tarjim.dub.audio import RATE
from tarjim.dub.lines import Line
from tarjim.job import Job

CROWDED = Line(38.2, 39.3, "voice1", "لأن الكثير من الناس يريدون التحدث إليه",
               "Because a lot of people want to talk to it.", 39.3)
TALKING = Line(4.0, 9.0, "voice2", "يشرفني", "I'm quite honored to be in this interview.", 9.0)


def voice(seconds: float) -> np.ndarray:
    return np.full(int(seconds * RATE), 0.1, dtype=np.float32)


def job() -> Job:
    return Job(Path("clip.mp4"), target="ar", dialect="saudi")


def rewriting(monkeypatch: pytest.MonkeyPatch, text: str) -> list[list[int]]:
    asked: list[list[int]] = []

    def rewrite(lines: list[Line], words: list[int], _language: str, _dialect: str) -> list[str]:
        asked.append(words)
        return [text for _ in lines]

    monkeypatch.setattr(refit, "rewrite", rewrite)
    return asked


def test_a_voice_far_longer_than_its_room_is_rewritten_to_fit_and_said_again(
        monkeypatch: pytest.MonkeyPatch) -> None:
    asked = rewriting(monkeypatch, "لأن ناس كثير يبون يكلمونه")
    lines, speech = refit.refit(lambda tried: [voice(1.0) for _ in tried], [CROWDED],
                                [voice(2.4)], job())
    assert asked == [[5]]  # 3 fit the time, but a round keeps 60% of its 7 words
    assert lines[0].text == "لأن ناس كثير يبون يكلمونه" and len(speech[0]) == RATE


def test_a_short_voice_is_never_given_words_the_speaker_did_not_say(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-11-25: made fuller, "فما راح يفوتك شي" came back "عشان كذا ما راح يفوتك أي شي"."""
    asked = rewriting(monkeypatch, "يشرفني والله إني أكون معكم في هالمقابلة")
    lines, _ = refit.refit(lambda tried: [voice(4.6) for _ in tried], [TALKING],
                           [voice(1.6)], job())
    assert not asked and lines == [TALKING]


def test_a_rewrite_that_drops_a_repeat_is_not_used(monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-11-25: "إيه، أكيد. إيه." came back "إيه، أكيد."."""
    said = Line(0.12, 1.4, "voice1", "إيه، أكيد. إيه.", "Yeah, sure. Yeah, yeah, yeah.", 1.0)
    rewriting(monkeypatch, "إيه، أكيد.")
    spoken: list[list[Line]] = []
    lines, _ = refit.refit(lambda tried: spoken.append(tried) or [voice(0.9) for _ in tried],
                           [said], [voice(1.6)], job())
    assert not spoken and lines == [said]


def test_a_voice_that_fits_is_left_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    asked = rewriting(monkeypatch, "غيره")
    lines, speech = refit.refit(lambda tried: [voice(1.0) for _ in tried], [CROWDED],
                                [voice(1.1)], job())
    assert not asked and lines == [CROWDED] and len(speech[0]) == int(1.1 * RATE)


def test_a_new_take_further_from_the_time_is_not_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    rewriting(monkeypatch, "أطول بكثير من الجملة الأولى")
    lines, speech = refit.refit(lambda tried: [voice(3.0) for _ in tried], [CROWDED],
                                [voice(2.2)], job())
    assert lines == [CROWDED] and len(speech[0]) == int(2.2 * RATE)


def test_it_tries_twice_at_most(monkeypatch: pytest.MonkeyPatch) -> None:
    asked = rewriting(monkeypatch, "ما زالت طويلة شوي عليه")
    refit.refit(lambda tried: [voice(2.0) for _ in tried], [CROWDED], [voice(2.2)], job())
    assert len(asked) == refit.ROUNDS == 2


def test_a_voice_that_fails_when_asked_again_keeps_the_first_take(
        monkeypatch: pytest.MonkeyPatch) -> None:
    rewriting(monkeypatch, "لأنهم يبون يكلمونه الحين كلهم")

    def broken(_tried: list[Line]) -> list[np.ndarray]:
        raise ConnectionError("the voice service dropped the connection")

    lines, speech = refit.refit(broken, [CROWDED], [voice(2.2)], job())
    assert lines == [CROWDED] and len(speech[0]) == int(2.2 * RATE)


def test_the_rewrite_keeps_every_repeat_and_asks_for_the_dialect() -> None:
    text = refit.prompt([CROWDED], [3], "Arabic", "saudi")
    assert "(saudi dialect)" in text and "about 3 words; keep: -" in text
    assert "every repetition, stutter and filler stays" in text
    assert "Because a lot of people want to talk to it." in text


def test_a_cancel_while_saying_again_still_stops_the_job(
        monkeypatch: pytest.MonkeyPatch) -> None:
    rewriting(monkeypatch, "لأنهم يبون يكلمونه الحين كلهم")
    cancelled: list[bool] = []

    class Stopped(Exception):
        pass

    def checkpoint() -> None:
        if cancelled:
            raise Stopped

    def cancel(_tried: list[Line]) -> list[np.ndarray]:
        cancelled.append(True)
        raise Stopped

    monkeypatch.setattr(refit, "checkpoint", checkpoint)
    with pytest.raises(Stopped):
        refit.refit(cancel, [CROWDED], [voice(2.4)], job())


def test_the_silence_around_a_voice_is_not_counted_as_its_length(
        monkeypatch: pytest.MonkeyPatch) -> None:
    asked = rewriting(monkeypatch, "غيره")
    padded = np.concatenate([np.zeros(RATE // 2, np.float32), voice(1.1),
                             np.zeros(RATE // 2, np.float32)])
    refit.refit(lambda tried: [voice(1.0) for _ in tried], [CROWDED], [padded], job())
    assert not asked


def test_only_free_voices_with_no_other_voice_behind_them_are_asked_again() -> None:
    """Gemini falls back to the clone voice when it fails: asked again, one speaker could end
    up with both voices."""
    from tarjim.dub import make

    assert set(make.AGAIN) == {"clone", "studio"}


def test_two_rounds_cannot_cut_a_line_below_what_the_first_may_lose(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-11-25: "وتدخل في صلب الموضوع بعيد عن المبالغات في تقنية المستهلك" (10 words) came back
    "تدخل في الصميم في التقنية" (5) over two rounds of 60% each."""
    answers = iter(["لأن ناس كثير يبون يكلمونه", "لأنهم يكلمونه"])
    monkeypatch.setattr(refit, "rewrite", lambda lines, *_: [next(answers) for _ in lines])
    lines, _ = refit.refit(lambda tried: [voice(2.0) for _ in tried], [CROWDED], [voice(2.4)],
                           job())
    assert lines[0].text == "لأن ناس كثير يبون يكلمونه"
