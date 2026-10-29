"""The parts of an exchange keep their order even when a model swaps them in its answer."""
from tarjim.languages import language
from tarjim.models import Cue, Word
from tarjim.rules import DEFAULT_RULES
from tarjim.translate.clean import in_order, map_results
from tarjim.translate.prompt import Brief, format_item


def test_each_part_of_an_exchange_is_sent_with_its_mark() -> None:
    first, second = [Word("Right.", 15.7, 15.9, "S2")], [Word("somewhere", 16.1, 16.4, "S1")]
    cue = Cue(15.7, 17.1, first + second, parts=[first, second])
    line = format_item(1, cue, Brief(language("ar"), "saudi", DEFAULT_RULES))
    assert line.endswith("[A] Right. || [B] somewhere")


def test_a_swapped_answer_is_put_back_in_order() -> None:
    assert in_order("[B] في الهند مثلاً || [A] صح") == "صح || في الهند مثلاً"
    assert map_results([{"id": 1, "text": "[B] two || [A] one"}], 1) == {1: "one || two"}


def test_marks_are_removed_and_unmarked_answers_left_as_they_are() -> None:
    assert in_order("(A) - إيه || (B) لا") == "إيه || لا"
    assert in_order("[A] جملة وحدة") == "جملة وحدة"
    assert in_order("صح || في الهند") == "صح || في الهند"
    assert in_order("[A] x || y") == "x || y"
