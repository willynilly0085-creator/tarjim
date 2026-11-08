"""The vote over listening passes, for every script and any number of passes (2026-11-08)."""
from itertools import permutations

from tarjim.asr.sanity import implausible, plausible_line
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import agreed, sane, spoken
from tarjim.listen.recover import fuller
from tarjim.listen.vote import majority, vote
from tarjim.models import Word
from tarjim.speakers import who

U = Utterance


def test_a_japanese_line_two_passes_heard_one_character_apart_is_kept() -> None:
    one = [U(1.0, 4.0, "S1", "今日はとても良い天気ですね")]
    two = [U(1.1, 4.1, "S1", "今日はとても良い天気だね")]
    assert [u.text for u in vote([one, two, []])] == ["今日はとても良い天気ですね"]
    assert spoken(one) == 13


def test_an_unspaced_line_is_judged_by_its_characters() -> None:
    assert not plausible_line(0.0, 5.0, "今日は" * 200)  # 600 characters in five seconds
    thai = "สวัสดีครับ วันนี้เราจะมาพูดคุยเกี่ยวกับเรื่องที่น่าสนใจมาก"  # 41 pieces, a fast 2 s
    assert plausible_line(0.0, 2.0, thai)
    pieces = [Word("วั", k / 18, k / 18 + 0.04) for k in range(18 * 120)]  # Thai, 18 a second
    assert not implausible(pieces)
    assert implausible([Word("今", k * 0.01, k * 0.01 + 0.009) for k in range(400)])


SPEECH = [U(k * 4.0, k * 4.0 + 3.5, "S1", f"line {k} has five words") for k in range(30)]
ENDING = U(125.0, 128.0, "S1", "and that is the whole story")
BROKEN = U(130.0, 200.0, "S1", "a line seventy seconds long")


def test_only_the_broken_line_of_a_pass_is_left_out() -> None:
    full = [*SPEECH, ENDING, BROKEN]
    assert sane(full) == [*SPEECH, ENDING]
    kept = agreed([full, [*SPEECH, ENDING], SPEECH])
    assert kept[-1].text == ENDING.text  # the pass with the broken line still backs the ending
    assert fuller([], [full]) == [*SPEECH, ENDING]


def test_an_extra_is_not_a_second_copy_of_a_line_the_vote_kept() -> None:
    base = [U(0.0, 3.0, "S1", "hello there friends and welcome back to the show"),
            U(30.0, 32.0, "S1", "today we cook rice"),
            U(60.0, 62.0, "S1", "hello there friends and welcome back")]
    again = [U(60.0, 63.0, "S1", "hello there friends and welcome back to the show")]
    middle = [U(30.1, 32.1, "S1", "today we cook rice"),
              U(60.1, 62.1, "S1", "hello there friends and welcome back")]
    kept = vote([base, again, middle, again], agree=2)
    assert [round(u.start) for u in kept if u.text.startswith("hello")] == [60]


TALK = [U(0.0, 2.0, "S1", "so where did you grow up"),
        U(2.5, 4.5, "S2", "in a small town by the sea"),
        U(5.0, 7.0, "S1", "that sounds lovely to me")]
LATE = U(10.0, 12.0, "S1", "it really was a quiet place")  # said by the base pass's S2


def swapped(lines: list[Utterance]) -> list[Utterance]:
    return [U(u.start, u.end, {"S1": "S2", "S2": "S1"}[u.speaker], u.text) for u in lines]


BASE_ONLY = U(20.0, 22.0, "S1", "and here is one more line from me")


def test_an_extra_takes_the_base_pass_speaker_it_was_heard_as() -> None:
    late = U(LATE.start, LATE.end, "S2", LATE.text)  # the base's S2, in the base's own numbering
    kept = vote([[*TALK, BASE_ONLY], [*swapped(TALK), LATE], [*TALK, late]])
    assert [u.speaker for u in kept if u.text == LATE.text] == ["S2"]


def test_an_unmatched_speaker_keeps_a_name_of_its_own() -> None:
    stranger = U(10.0, 12.0, "S3", LATE.text)
    kept = vote([[*TALK, BASE_ONLY], [*TALK, stranger], [*TALK, stranger]])
    label = next(u.speaker for u in kept if u.text == LATE.text)
    assert label != "S3" and label.startswith("S3") and who(label) == label


def test_the_agreement_needed_is_a_majority_of_the_passes() -> None:
    assert [majority(n) for n in range(1, 6)] == [1, 2, 2, 3, 3]
    line = U(1.0, 3.0, "S1", "only two of five heard this")
    common = U(5.0, 7.0, "S1", "everyone heard this one line")
    runs = [[line, common], [line, common], [common], [common], [common]]
    assert [u.text for u in vote(runs)] == [common.text]
    assert vote([*runs[:2], [line, common], *runs[3:]])[0].text == line.text


def test_the_order_of_the_passes_does_not_change_the_vote() -> None:
    a = [U(10.0, 13.0, "S3", "Maybe like once every three months."),
         U(12.1, 13.0, "S1", "Nice."), U(17.0, 18.0, "S1", "Nice.")]
    b = [U(10.2, 13.2, "S4", "Maybe once every three months"), U(17.6, 18.6, "S2", "Nice."),
         U(30.0, 31.0, "S4", "See you.")]
    c = [U(10.0, 12.0, "S2", "Maybe like once every like three months."),
         U(17.0, 18.0, "S1", "Nice.")]
    first, settled = vote([a, b, c]), agreed([a, b, c])
    assert all(vote(list(p)) == first for p in permutations([a, b, c]))
    assert all(agreed(list(p)) == settled for p in permutations([a, b, c]))
