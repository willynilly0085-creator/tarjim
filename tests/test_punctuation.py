from dataclasses import dataclass

from tarjim.asr.qwen import attach_punctuation


@dataclass
class Item:
    text: str
    start_time: float
    end_time: float


def test_punctuation_is_restored_on_aligned_words() -> None:
    items = [Item("Okay", 0.1, 0.4), Item("I", 0.5, 0.6), Item("asked", 0.6, 0.9)]
    words = attach_punctuation("Okay, I asked.", items)
    assert [w.text for w in words] == ["Okay,", "I", "asked."]
    assert words[2].end == 0.9


def test_split_aligner_tokens_are_merged_back() -> None:
    items = [Item("it", 1.0, 1.1), Item("s", 1.1, 1.2), Item("gross", 1.3, 1.7)]
    words = attach_punctuation("it's gross", items)
    assert [(w.text, w.start, w.end) for w in words] == [("it's", 1.0, 1.2), ("gross", 1.3, 1.7)]
