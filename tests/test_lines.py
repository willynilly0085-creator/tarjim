from tarjim.lines import balance_lines, display_lines


def test_dialogue_renders_one_dashed_line_per_speaker() -> None:
    assert display_lines("إيه؟ || - إيه.") == ["- إيه؟", "- إيه."]


def test_short_text_stays_one_line() -> None:
    assert balance_lines("سألت الكل كم مرة يتروشون؟") == ["سألت الكل كم مرة يتروشون؟"]


def test_long_text_splits_into_two_balanced_lines() -> None:
    text = "ولا مرة، مرتين بالسنة، أسبوعياً، أنا عن نفسي أبداً ولا مرة"
    top, bottom = balance_lines(text)
    assert abs(len(top) - len(bottom)) <= 12
    assert f"{top} {bottom}" == text


def test_prefers_breaking_after_punctuation() -> None:
    top, _ = balance_lines("على الأقل مرة بالشهر، وبعضهم يقول كل ثلاث شهور تقريباً")
    assert top.endswith("،")
