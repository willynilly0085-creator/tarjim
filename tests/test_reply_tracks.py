"""Replies said over a turn, in the orders the listeners really give them (2026-11-08): a reply
followed by the replier's own next turn, a reply slotted in by its start with no speaker
labels, and a quick answer that only touches the end of a finished sentence."""
import pytest

from tarjim.dialogue import split_at
from tarjim.models import Cue, Word
from tarjim.rules import DEFAULT_RULES
from tarjim.segment import build_cues

TOLD = "I told him to leave early before the traffic gets bad. He did not listen to me at all."
HOST = "we went to the market and bought bread."


def said(text: str, start: float, pace: tuple[float, float], who: str) -> list[Word]:
    """Each word `step` after the last, lasting `length`."""
    step, length = pace
    return [Word(token, start + k * step, start + k * step + length, who)
            for k, token in enumerate(text.split())]


def holding(cues: list[Cue], word: str) -> Cue:
    return next(c for c in cues if any(w.text == word for w in c.words))


@pytest.mark.parametrize(("first", "second"), [("S1", "S2"), ("", "")])
def test_a_reply_followed_by_the_repliers_next_turn_is_shown_at_its_own_time(
        first: str, second: str) -> None:
    turn = said(TOLD, 0.0, (0.5, 0.35), first)  # 0.00 to 9.35 s
    reply = said("No way.", 4.0, (0.35, 0.3), second)
    later = said("So what happened after that?", 10.5, (0.4, 0.35), second)
    cues = build_cues([*turn, *reply, *later], cuts=[])
    shown = holding(cues, "No")
    assert shown.start <= 4.0 + 1e-9 <= shown.end
    assert ["No", "way."] in [[w.text for w in part] for part in shown.parts]
    assert all(w.text not in {"He", "listen", "So"} for w in shown.words)
    assert all(len(c.parts) <= 2 for c in cues)


def test_an_unlabelled_reply_slotted_by_its_start_is_a_part_not_mixed_in() -> None:
    words = said(HOST, 0.0, (0.5, 0.4), "")
    reply = Word("Really?", 1.6, 2.2, "")
    cues = build_cues([*words[:4], reply, *words[4:]], cuts=[])
    assert len(cues) == 1
    assert [[w.text for w in part] for part in cues[0].parts] == [HOST.split(), ["Really?"]]


def test_unlabelled_words_that_barely_touch_stay_one_sentence() -> None:
    words = said(HOST, 0.0, (0.5, 0.4), "")
    touching = [Word(w.text, w.start, w.end + 0.2) for w in words]  # 0.1 s into the next
    cues = build_cues(touching, cuts=[])
    assert [c.source for c in cues] == [HOST]


def test_a_quick_answer_at_the_end_of_a_finished_sentence_keeps_the_sentence_whole() -> None:
    plan = "The whole plan was a total mess from the start, I think."
    turn = said(plan, 0.0, (0.4, 0.35), "S1")  # "think." is 4.40 to 4.75
    answer = [Word("Yes,", 4.3, 4.7, "S2"), Word("of", 4.8, 5.1, "S2"),
              Word("course.", 5.2, 5.85, "S2")]
    later = said("Then we left.", 9.0, (0.4, 0.35), "S1")
    cues = build_cues([*turn, *answer, *later], cuts=[])
    assert cues[0].source == plan
    assert holding(cues, "course.").source == "Yes, of course."


def test_a_turns_word_said_before_the_reply_ends_stays_with_the_turn() -> None:
    turn = said("one two three four five six", 0.0, (0.5, 0.4), "S1")
    host = Cue(0.0, 2.9, list(turn), parts=[list(turn)])
    reply = [Word("Wow", 1.2, 1.8, "S3")]  # "four" starts at 1.5, while "Wow" is said
    pieces = split_at(host, reply, DEFAULT_RULES)
    kept = [w.text for w in pieces[0].words]
    assert kept == ["one", "two", "three", "four"]
    assert pieces[1].words[0].text == "Wow"

