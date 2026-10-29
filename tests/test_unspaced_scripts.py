"""Chinese, Japanese and Thai are written without spaces: their words are timed and cut one
character at a time, as the local aligner times them, and joined back without spaces."""
from dataclasses import dataclass

from tarjim.asr.align import proportional
from tarjim.asr.qwen import attach_punctuation
from tarjim.listen.gemini_listen import Utterance, parse
from tarjim.models import Word, join_words
from tarjim.scripts import split_words
from tarjim.segment import build_cues


@dataclass
class Item:
    text: str
    start_time: float
    end_time: float


def test_unspaced_text_splits_into_characters_with_their_punctuation() -> None:
    assert split_words("「你好」 OK吗？ เป็น") == ["「你", "好」", "OK", "吗？", "เ", "ป็", "น"]
    assert split_words("It's fine.") == ["It's", "fine."]


def test_words_of_unspaced_scripts_join_without_spaces() -> None:
    said = [Word("你", 0, 1), Word("好", 1, 2), Word("OK", 2, 3), Word("吗", 3, 4)]
    assert join_words(said) == "你好 OK 吗"


def test_chinese_is_timed_character_by_character() -> None:
    items = [Item(ch, k * 0.3, k * 0.3 + 0.25) for k, ch in enumerate("你好我很好")]
    words = attach_punctuation("你好。我很好！", items)
    assert [w.text for w in words] == ["你", "好。", "我", "很", "好！"]
    assert (words[2].start, words[4].end) == (0.6, 1.45)


def test_chinese_sentences_end_at_their_own_full_stop() -> None:
    said = [Word("你", 0.0, 0.5), Word("好。", 0.5, 1.0), Word("我", 1.1, 1.6),
            Word("很", 1.6, 2.1), Word("好。", 2.1, 2.6)]
    assert [c.source for c in build_cues(said, cuts=[])] == ["你好。", "我很好。"]


def test_a_long_chinese_utterance_is_spread_over_its_time() -> None:
    words = proportional(Utterance(0.0, 4.0, "S1", "我今天很高兴见到你们"))
    assert len(words) == 10 and abs(words[-1].end - 4.0) < 1e-9


def test_punctuation_written_apart_stays_with_its_word() -> None:
    items = [Item("Vraiment", 0.1, 0.6), Item("Oui", 1.0, 1.3)]
    words = attach_punctuation("Vraiment ? Oui !", items)
    assert [w.text for w in words] == ["Vraiment ?", "Oui !"]
    assert (words[0].start, words[0].end) == (0.1, 0.6)


def test_a_reply_given_no_length_gets_one_from_its_words() -> None:
    yes = parse({"start": 4.0, "end": 4.0, "speaker": "S2", "text": "Yes."})
    assert yes is not None and yes.start == 4.0 and 4.2 <= yes.end <= 5.0
