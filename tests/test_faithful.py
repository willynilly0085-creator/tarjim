"""What can be told of a translation without a model: a number that is gone, a glossary name not
written as the person set it, a line much shorter than its speech next to the clip's other
lines, and a line shown as it was said among translated ones (2026-11-14)."""
from tarjim.models import Cue, Word
from tarjim.translate.faithful import numbers, unfaithful


def cue(source: str, text: str, start: float = 0.0) -> Cue:
    words = [Word(w, start + k * 0.4, start + (k + 1) * 0.4) for k, w in enumerate(source.split())]
    return Cue(start, start + 4.0, words, text)


def test_a_number_is_read_the_same_however_it_is_written() -> None:
    assert numbers("in 2019, 1,250 people and 4 075 more") == ["2019", "1250", "4075"]
    assert numbers("day 2019 150 came") == ["2019", "150"]  # two numbers, not one grouped
    assert numbers("سنة ٢٠١٩ و۱۵ شخص") == ["2019", "15"]
    assert numbers("3 of them, 100 or 2,000,000") == []  # small or round: often worded


def test_a_number_missing_from_the_translation_is_listed() -> None:
    kept = cue("He paid 350 million in 2019.", "دفع ٣٥٠ مليون سنة ٢٠١٩.")
    lost = cue("He paid 350 million in 2019.", "دفع 530 مليون سنة 2019.")
    assert unfaithful([kept, lost], ()) == [2]


def test_a_number_said_twice_need_be_written_once() -> None:
    once = cue("in 2019, in 2019 we left", "طلعنا سنة 2019")
    assert unfaithful([once], ()) == []


def test_a_glossary_name_must_be_written_as_the_person_set_it() -> None:
    glossary = (("tarjim", "ترجم"), ("Staley", "ستيلي"))
    right = cue("We asked Staley about Tarjim.", "سألنا ستيلي عن ترجم.")
    wrong = cue("We asked Staley about it.", "سألنا ستالي عنه.")
    other = cue("Unstaleyed words are no match.", "كلام ثاني.")
    assert unfaithful([right, wrong, other], glossary) == [2]


def test_a_line_much_shorter_than_its_speech_beside_the_others_is_listed() -> None:
    full = [cue(f"this is line number {n} and it says quite a lot of things",
                f"هذا السطر رقم {n} ويقول أشياء كثيرة جداً", n * 5.0) for n in range(6)]
    cut = cue("this is the last line and it says quite a lot of things too", "الأخير", 30.0)
    assert unfaithful([*full, cut], ()) == [7]


def test_a_short_reply_is_never_listed_as_shortened() -> None:
    full = [cue(f"this is line number {n} and it says quite a lot of things",
                f"هذا السطر رقم {n} ويقول أشياء كثيرة جداً", n * 5.0) for n in range(6)]
    assert unfaithful([*full, cue("Yes of course.", "إي", 30.0)], ()) == []


def test_a_line_shown_as_said_among_translated_ones_is_listed() -> None:
    lines = [cue("the first line of the talk", "السطر الأول من الكلام"),
             cue("the second line of the talk", "the second line of the talk", 5.0),
             cue("the third line of the talk", "السطر الثالث من الكلام", 10.0)]
    assert unfaithful(lines, ()) == [2]


def test_a_clip_subtitled_in_its_own_language_is_not_all_listed() -> None:
    lines = [cue(f"line number {n} of the talk", f"Line number {n} of the talk.", n * 5.0)
             for n in range(4)]
    assert unfaithful(lines, ()) == []


def test_a_line_with_no_translation_is_left_to_its_own_note() -> None:
    assert unfaithful([cue("In 2019 he left.", "")], ()) == []
