from tarjim.dub import keep


def test_every_filler_and_repeat_must_stay() -> None:
    assert not keep.keeps("أوه، واو. إيش الملاحظات؟", "واو. إيش الملاحظات؟")
    assert not keep.keeps("إيه، أكيد. إيه.", "إيه، أكيد.")
    assert keep.keeps("إيه، أكيد. إيه.", "إيه أكيد إيه")


def test_a_line_may_not_lose_more_than_forty_percent_of_its_words() -> None:
    old = "بس هنا، أقدر أوريك هالأشياء كلها."
    assert not keep.keeps(old, "بس أوريك.") and keep.keeps(old, "بس هنا أوريك كلها.")


def test_diacritics_do_not_hide_a_kept_word() -> None:
    assert keep.keeps("إيه إيه، تمام", "إِيه إيه تَمام")


def test_the_words_to_keep_are_listed_with_how_often() -> None:
    assert keep.listed("إيه، أكيد. إيه.") == "إيه ×2"
    assert keep.listed("لأن الكثير من الناس") == ""
