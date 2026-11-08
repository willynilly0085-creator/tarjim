"""Every subtitle stays up long enough to read and never runs into the next (2026-11-08).
Before, a line that started within 83 ms of the next one was shown for a microsecond, and a
line right before a shot change flashed."""
import random
from collections import Counter
from itertools import pairwise

import pytest

from tarjim.dialogue import MAX_SPEAKERS
from tarjim.models import Cue, Word
from tarjim.rules import DEFAULT_RULES, Rules
from tarjim.segment import build_cues, fit_timing

RULES = DEFAULT_RULES
TOLERANCE = 1e-6


def cue(text: str, start: float, end: float, speaker: str = "S1") -> Cue:
    words = [Word(text, start, end, speaker)]
    return Cue(start, end, list(words), parts=[list(words)])


def dialogue(first: Cue, second: Cue) -> Cue:
    return Cue(first.start, second.end, first.words + second.words,
               parts=[*first.parts, *second.parts])


def test_two_lines_started_together_become_one_exchange_not_a_flash() -> None:
    fitted = fit_timing([cue("Oh.", 10.0, 10.3, "S1"), cue("Hey.", 10.05, 10.4, "S2")], RULES)
    assert len(fitted) == 1 and fitted[0].is_dialogue
    assert fitted[0].duration >= RULES.min_duration


def test_one_speaker_said_twice_quickly_becomes_one_part() -> None:
    fitted = fit_timing([cue("Go.", 10.0, 10.3), cue("Now.", 10.1, 10.4)], RULES)
    assert len(fitted) == 1 and len(fitted[0].parts) == 1
    assert fitted[0].source == "Go. Now."


def test_a_third_voice_that_cannot_join_still_gets_time_to_read() -> None:
    both = dialogue(cue("Oh.", 10.0, 10.1, "S1"), cue("Ah.", 10.02, 10.3, "S2"))
    fitted = fit_timing([both, cue("Hey.", 10.05, 10.4, "S3")], RULES)
    assert len(fitted) == 2
    assert fitted[0].duration >= RULES.min_readable - TOLERANCE
    assert fitted[0].end + RULES.min_gap <= fitted[1].start + TOLERANCE
    assert fitted[1].duration >= RULES.min_duration - TOLERANCE


def test_a_line_right_before_a_shot_change_stays_long_enough() -> None:
    fitted = fit_timing([cue("No.", 12.0, 12.2, "S1"),
                         cue("a long answer after the cut", 14.0, 19.0, "S2")], RULES, [12.3])
    assert fitted[0].duration >= RULES.min_duration - TOLERANCE


def test_a_squeezed_line_starts_a_little_early_instead_of_flashing() -> None:
    before = cue("Before.", 3.0, 4.0, "S2")
    hi = cue("Hi.", 5.0, 5.2, "S1")
    after = cue("a long turn of somebody else", 5.75, 11.5, "S2")
    fitted = fit_timing([before, hi, after], RULES)
    assert [c.source for c in fitted] == ["Before.", "Hi.", "a long turn of somebody else"]
    assert 4.8 - TOLERANCE <= fitted[1].start < 5.0
    assert fitted[1].duration >= RULES.min_duration - TOLERANCE


def test_an_early_start_never_crosses_a_shot_change() -> None:
    before = cue("Before.", 3.0, 4.0, "S2")
    hi = cue("Hi.", 5.0, 5.2, "S1")
    after = cue("a long turn of somebody else", 5.75, 11.9, "S2")
    fitted = fit_timing([before, hi, after], RULES, [4.95])
    shown = next(c for c in fitted if "Hi." in c.source)
    assert shown.start >= 4.95
    assert shown.duration >= RULES.min_duration - TOLERANCE


def test_a_question_answered_over_its_end_becomes_one_exchange() -> None:
    """2026-10-29 the answer waited 0.88 s for the question; now both are shown together."""
    asked = cue("هذا قصدك؟", 234.74, 237.78, "S2")
    answer = cue("أشوف التدخل البشري كان هائل", 234.8, 239.0, "S1")
    fitted = fit_timing([asked, answer], RULES)
    assert len(fitted) == 1 and fitted[0].is_dialogue
    assert fitted[0].start == pytest.approx(234.74) and fitted[0].end >= 239.0


def stream(seed: int) -> tuple[list[Word], list[float]]:
    """Turns, quick replies said over them, replies slotted in by start, and turns that
    arrive out of order, as the listeners give them."""
    pick = random.Random(seed)
    speakers = ["S1", "S2", "S3"] if pick.random() < 0.8 else [""]
    words: list[Word] = []
    at = 0.0
    for turn in range(pick.randint(1, 12)):
        who = pick.choice(speakers)
        said = [Word(f"w{turn}.{k}" + ("." if pick.random() < 0.2 else ""),
                     at + k * 0.35, at + k * 0.35 + pick.uniform(0.0, 0.5), who)
                for k in range(pick.randint(1, 14))]
        if pick.random() < 0.3 and len(said) > 2:
            middle = said[len(said) // 2]
            reply = [Word(f"r{turn}", middle.start + 0.1, middle.start + pick.uniform(0.1, 0.9),
                          pick.choice(speakers))]
            said = said + reply if pick.random() < 0.5 else (
                said[:len(said) // 2 + 1] + reply + said[len(said) // 2 + 1:])
        words += said
        at = said[-1].end + pick.uniform(-0.6, 3.0)
    if pick.random() < 0.2:
        cut = pick.randrange(len(words))
        words = words[cut:] + words[:cut]
    cuts = sorted(pick.uniform(0.0, at + 2) for _ in range(pick.randint(0, 4)))
    return words, cuts


def check(cues: list[Cue], words: list[Word], rules: Rules) -> None:
    assert Counter(w for c in cues for w in c.words) == Counter(words)
    for one in cues:
        assert one.end - one.start >= rules.min_duration - TOLERANCE, one
        assert 1 <= len(one.parts) <= MAX_SPEAKERS
        assert [w for part in one.parts for w in part] == one.words
    for first, second in pairwise(cues):
        assert first.start <= second.start
        assert first.end + rules.min_gap <= second.start + TOLERANCE, (first, second)


@pytest.mark.parametrize("seed", range(400))
def test_no_stream_of_words_gives_a_flash_or_an_overlap(seed: int) -> None:
    words, cuts = stream(seed)
    check(build_cues(words, cuts, RULES), words, RULES)


@pytest.mark.parametrize("seed", range(0, 400, 7))
def test_narrow_lines_keep_the_same_promise(seed: int) -> None:
    from dataclasses import replace

    words, cuts = stream(seed)
    rules = replace(RULES, line_chars=13, max_source_chars=26, spaced=False)
    check(build_cues(words, cuts, rules), words, rules)


@pytest.mark.parametrize("seed", range(3, 400, 11))
def test_words_of_an_unspaced_script_keep_the_same_promise(seed: int) -> None:
    from dataclasses import replace

    given, cuts = stream(seed)
    words = [replace(w, text=chr(0x4E00 + k) + ("。" if w.text.endswith(".") else ""))
             for k, w in enumerate(given)]
    rules = replace(RULES, line_chars=16, max_source_chars=32, spaced=False)
    check(build_cues(words, cuts, rules), words, rules)
