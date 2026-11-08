"""Where heard words become subtitles (2026-11-08): words that arrive out of order are put back
in order, and a short reply said over another turn becomes a part of that turn's subtitle
instead of being mixed into the host's sentence."""
from tarjim.dialogue import Piece, join, new_cue
from tarjim.models import Word
from tarjim.segment import build_cues

HOST = ["we", "went", "to", "the", "market", "and", "bought", "bread."]


def host(speaker: str = "S1", start: float = 0.0) -> list[Word]:
    return [Word(text, start + k * 0.5, start + k * 0.5 + 0.4, speaker)
            for k, text in enumerate(HOST)]


def test_a_reply_the_aligner_put_after_the_turn_is_a_part_of_that_turn() -> None:
    reply = Word("Really?", 1.6, 2.0, "S2")
    cues = build_cues([*host(), reply], cuts=[])
    assert len(cues) == 1
    assert [[w.text for w in part] for part in cues[0].parts] == [HOST, ["Really?"]]
    assert cues[0].source == f"- {' '.join(HOST)} || - Really?"


def test_a_reply_slotted_by_its_start_into_the_turn_is_not_mixed_into_the_sentence() -> None:
    words = host()
    reply = Word("Really?", 1.6, 2.2, "S2")  # still talking when the host goes on at 2.0
    cues = build_cues([*words[:4], reply, *words[4:]], cuts=[])
    assert len(cues) == 1
    assert [w.text for w in cues[0].parts[0]] == HOST
    assert [w.text for w in cues[0].parts[1]] == ["Really?"]


def test_a_reply_in_a_pause_of_the_turn_is_a_turn_of_its_own() -> None:
    first = [Word("Right", 0.0, 0.4, "S1"), Word("then.", 0.5, 0.9, "S1")]
    later = [Word("We", 3.0, 3.3, "S1"), Word("go", 3.4, 3.7, "S1"), Word("now.", 3.8, 4.2, "S1")]
    reply = Word("Okay.", 1.5, 1.9, "S2")
    cues = build_cues([*first, reply, *later], cuts=[])
    assert [w.text for c in cues for w in c.words] == ["Right", "then.", "Okay.", "We", "go",
                                                       "now."]


def test_turns_that_arrive_out_of_order_are_put_back_in_order() -> None:
    later = [Word(t, 10.0 + k * 0.4, 10.3 + k * 0.4, "S2") for k, t in enumerate(
        ["and", "then", "we", "left."])]
    earlier = [Word(t, 1.0 + k * 0.4, 1.3 + k * 0.4, "S1") for k, t in enumerate(
        ["first", "we", "ate."])]
    cues = build_cues([*later, *earlier], cuts=[])
    assert [c.source for c in cues] == ["first we ate.", "and then we left."]
    assert cues[0].end <= cues[1].start


def test_two_long_turns_said_at_once_stay_whole() -> None:
    asked = [Word(w, 234.7 + k * 0.4, 234.9 + k * 0.4, "S2")
             for k, w in enumerate(["Is", "that", "kind", "of", "what", "you're", "saying?"])]
    answer = [Word(w, 234.8 + k * 0.3, 235.0 + k * 0.3, "S1")
              for k, w in enumerate(["So", "so", "so", "I", "think", "the", "level"])]
    cues = build_cues(asked + answer, cuts=[])
    sources = " ".join(c.source for c in cues)
    assert "Is that kind of what you're saying?" in sources
    assert "So so so I think the level" in sources


def test_a_reply_that_would_be_a_third_part_starts_a_subtitle_of_its_own() -> None:
    right = Word("Right.", 0.0, 0.4, "S1")
    turn = host("S2", start=0.8)
    wow = Word("Wow", 2.4, 2.9, "S3")  # said over "the market"
    cues = build_cues([right, *turn[:4], wow, *turn[4:]], cuts=[])
    assert all(len(c.parts) <= 2 for c in cues)
    assert sorted(w.text for c in cues for w in c.words) == sorted(["Right.", *HOST, "Wow"])
    started = next(c for c in cues if c.words[0].text == "Wow")
    assert started.start <= 2.4 and [w.text for w in started.parts[0]] == ["Wow"]
    assert all(len({w.speaker for w in part}) == 1 for c in cues for part in c.parts)


def test_a_joined_part_never_ends_its_subtitle_before_its_own_words() -> None:
    cue = new_cue(Piece([Word("a", 0.0, 2.0, "S1")]))
    join(cue, Piece([Word("b", 1.0, 1.4, "S2")], new_speaker=True))
    assert cue.end == 2.0


def test_a_new_subtitle_ends_with_its_longest_word_not_its_last() -> None:
    cue = new_cue(Piece([Word("a", 0.0, 2.0), Word("b", 1.0, 1.4)]))
    assert cue.end == 2.0
