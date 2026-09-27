from itertools import pairwise

from tarjim.models import Word
from tarjim.rules import Rules
from tarjim.segment import build_cues


def words(*items: tuple[str, float, float]) -> list[Word]:
    return [Word(t, s, e) for t, s, e in items]


def test_pause_splits_speakers() -> None:
    ws = words(("Not", 7.4, 7.8), ("enough.", 7.8, 8.3), ("Maybe", 9.8, 10.1),
               ("once", 10.1, 10.6), ("a", 10.6, 10.7), ("year.", 10.7, 11.2))
    cues = build_cues(ws, cuts=[])
    assert [c.source for c in cues] == ["Not enough.", "Maybe once a year."]


def test_shot_cut_splits_without_pause() -> None:
    ws = words(("never", 34.6, 35.2), ("again", 35.2, 35.85), ("twice", 36.0, 36.4),
               ("a", 36.4, 36.5), ("year", 36.5, 37.0))
    cues = build_cues(ws, cuts=[35.9])
    assert [c.source for c in cues] == ["never again", "twice a year"]


def test_short_lines_across_a_cut_become_dialogue() -> None:
    ws = words(("never", 35.2, 35.5), ("again", 35.5, 35.85), ("twice", 36.0, 36.4))
    cues = build_cues(ws, cuts=[35.9])
    assert [c.source for c in cues] == ["- never again || - twice"]


def test_sentence_end_with_pause_splits() -> None:
    ws = words(("Once", 29.0, 29.4), ("a", 29.4, 29.5), ("week.", 29.5, 30.1),
               ("Once", 30.8, 31.2), ("a", 31.2, 31.3), ("week?", 31.3, 31.9))
    cues = build_cues(ws, cuts=[])
    assert [c.source for c in cues] == ["Once a week.", "Once a week?"]


def test_pause_inside_unfinished_sentence_keeps_it_together() -> None:
    ws = words(("Longer", 55.6, 55.9), ("than", 55.9, 56.0), ("that.", 57.44, 57.9))
    cues = build_cues(ws, cuts=[])
    assert [c.source for c in cues] == ["Longer than that."]


def test_rapid_exchange_becomes_one_dialogue_subtitle() -> None:
    ws = words(("Yeah?", 28.0, 28.16), ("Yeah.", 28.56, 28.72))
    cues = build_cues(ws, cuts=[28.4])
    assert len(cues) == 1
    assert cues[0].is_dialogue
    assert cues[0].source == "- Yeah? || - Yeah."


def test_speaker_labels_decide_dialogue_not_cuts() -> None:
    ws = [Word("Never.", 32.5, 33.2, "S9"), Word("Never?", 34.0, 34.5, "S1")]
    cues = build_cues(ws, cuts=[])
    assert [c.source for c in cues] == ["- Never. || - Never?"]


def test_cut_inside_one_speaker_is_not_dialogue() -> None:
    ws = [Word("At", 44.8, 45.0, "S12"), Word("least", 45.0, 45.3, "S12"),
          Word("once.", 45.3, 45.6, "S12"), Word("Sometimes", 45.9, 46.4, "S12")]
    cues = build_cues(ws, cuts=[45.75])
    assert not any(c.is_dialogue for c in cues)


def test_labelled_speaker_is_never_split_by_a_cut_mid_sentence() -> None:
    ws = [Word("Dude,", 40.9, 41.0, "S11"), Word("so", 41.05, 41.2, "S11"),
          Word("me", 41.2, 41.4, "S11"), Word("personally,", 41.4, 41.9, "S11"),
          Word("never.", 41.9, 42.7, "S11")]
    cues = build_cues(ws, cuts=[41.02])
    assert [c.source for c in cues] == ["Dude, so me personally, never."]


def test_long_block_is_split_under_max_duration() -> None:
    ws = [Word(f"w{i}", i * 0.5, i * 0.5 + 0.4) for i in range(20)]
    cues = build_cues(ws, cuts=[], rules=Rules())
    assert all(c.duration <= 6.0 + 1e-6 for c in cues)
    assert sum(len(c.words) for c in cues) == 20


def test_every_cue_ends_after_it_starts_and_never_overlaps() -> None:
    ws = words(("never.", 41.8, 44.16), ("Never.", 44.16, 44.16), ("He", 44.16, 44.16),
               ("said", 44.16, 44.3), ("once.", 44.3, 45.1), ("Sometimes.", 45.44, 45.84))
    cues = build_cues(ws, cuts=[44.2])
    assert all(c.end > c.start for c in cues)
    assert all(a.end <= b.start for a, b in pairwise(cues))


def test_no_word_is_lost_or_duplicated() -> None:
    ws = words(("a", 0, 0.2), ("b.", 0.3, 0.5), ("c", 2, 2.2), ("d", 2.25, 2.4))
    cues = build_cues(ws, cuts=[2.23])
    assert [w.text for c in cues for w in c.words] == ["a", "b.", "c", "d"]


def labelled(*items: tuple[str, float, float, str]) -> list[Word]:
    return [Word(t, s, e, who) for t, s, e, who in items]


def test_subtitle_never_runs_into_the_next_shot() -> None:
    ws = labelled(("three", 12.2, 12.5, "S3"), ("months.", 12.5, 13.1, "S3"),
                  ("Once", 16.6, 16.9, "S4"))
    cues = build_cues(ws, cuts=[13.47])
    assert cues[0].end <= 13.47


def test_reaction_before_a_cut_is_not_glued_to_a_long_line_after_it() -> None:
    ws = labelled(("Nice.", 17.6, 18.0, "S1"), ("Oh", 18.8, 19.0, "S5"), ("my", 19.0, 19.2, "S5"),
                  ("gosh,", 19.2, 19.9, "S5"), ("18", 19.9, 20.2, "S5"),
                  ("times.", 20.2, 21.1, "S5"))
    cues = build_cues(ws, cuts=[18.77])
    assert [c.source for c in cues] == ["Nice.", "Oh my gosh, 18 times."]
    assert cues[0].end <= 18.77


def test_a_short_sentence_joins_the_closer_neighbour() -> None:
    ws = words(("It", 14.64, 14.72), ("follows", 16.16, 16.7), ("every", 16.72, 16.95),
               ("cut.", 16.96, 17.3), ("Want", 18.28, 18.36), ("it", 18.36, 18.44),
               ("dubbed?", 18.44, 18.9), ("Every", 19.16, 19.4), ("speaker", 19.4, 19.8),
               ("gets", 19.8, 19.96), ("a", 19.96, 20.04), ("voice.", 20.04, 20.9))
    cues = build_cues(ws, cuts=[])
    assert [c.source for c in cues][-1] == "Want it dubbed? Every speaker gets a voice."


def test_japanese_lines_do_not_break_inside_a_word() -> None:
    from tarjim.languages import language
    from tarjim.lines import balance_lines, script_of
    from tarjim.rules import rules_for

    rules = rules_for(language("ja"))
    for text in ("どんな動画も母語で話せたら？", "タルジムは3回聞いて、単語ごとに投票します"):
        top, bottom = balance_lines(text, rules)
        pair = (script_of(top[-1]), script_of(bottom[0]))
        assert pair not in {("kanji", "kanji"), ("kanji", "hiragana"), ("katakana", "katakana")}
        assert bottom[0] not in "、。？！ー"
