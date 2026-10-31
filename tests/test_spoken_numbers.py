from tarjim.asr.numbers import said


def test_a_countdown_is_spelled_in_the_language_that_was_heard() -> None:
    assert said(["Осталось", "3", "секунды,", "2,", "1,", "0!"], "Russian") == [
        "Осталось", "три", "секунды,", "два,", "один,", "ноль!"]


def test_a_number_written_in_groups_is_one_number() -> None:
    assert said(["Высота", "4", "000", "метров."], "Russian") == [
        "Высота", "четыре тысячи", "", "метров."]
    assert said(["about", "3,000", "people"], "English") == ["about", "three thousand", "people"]


def test_a_language_without_spelled_numbers_keeps_its_digits() -> None:
    assert said(["7", "x"], "Klingon") == ["7", "x"]


def test_a_line_without_numbers_is_left_as_it_is() -> None:
    words = ["no", "numbers", "here"]
    assert said(words, "English") is words
