"""The words this computer heard are used only where the sound confirms them (asr/confirm.py,
2026-11-08): on the Arabic bench clips its times drifted up to 11 s early and half its words had
no length, and the anchor, the aligner and the coverage check trusted them because the text
matched."""
import numpy as np

from tarjim.asr.confirm import FOUND, Kept, confirmed
from tarjim.asr.ctc import FRAME
from tarjim.models import Word

LETTERS = "abcdefghijklmnopqrstuvwxyz"
SIZE = 4 + len(LETTERS)
SECONDS = 120.0
STEP = 3  # frames each letter is said for
PHRASES = ["alpha bravo charlie", "delta echo foxtrot", "golf hotel india", "juliet kilo lima",
           "mike november oscar", "papa quebec romeo"]


def tokens(text: str) -> list[int]:
    return [4 + LETTERS.index(ch) for ch in text.lower() if ch in LETTERS]


def laid(text: str, start: float) -> list[Word]:
    """The phrase's words one after another from `start`, each as long as its letters."""
    words, at = [], start
    for part in text.split():
        end = at + STEP * FRAME * len(part)
        words.append(Word(part, round(at, 2), round(end, 2)))
        at = end + 0.1
    return words


def sound(said: list[tuple[str, float]], faint: float = 0.0) -> np.ndarray:
    """The clip's letters: each phrase heard where it is said, all else silence; a faint
    phrase's letters are heard with that likelihood only."""
    probs = np.full((int(SECONDS / FRAME), SIZE), 0.02 / SIZE)
    probs[:, 0] = 0.98
    for text, start in said:
        for word in laid(text, start):
            frame = round(word.start / FRAME)
            for k, token in enumerate(tokens(word.text)):
                rows = slice(frame + STEP * k, frame + STEP * (k + 1))
                probs[rows, 0], probs[rows, token] = 1.0 - (faint or 0.98), faint or 0.98
    return np.log(probs)


def heard(said: list[tuple[str, float]]) -> list[Word]:
    return [w for text, start in said for w in laid(text, start)]


def check(said: list[tuple[str, float]], timed: list[Word], faint: float = 0.0) -> Kept:
    return confirmed(sound(said, faint), timed, tokens)


AT = [(PHRASES[k], 1.0 + 3.0 * k) for k in range(5)]  # five phrases said 1 s to 13 s


def test_words_said_where_they_are_timed_are_all_kept() -> None:
    kept = check(AT, heard(AT))
    assert kept.words == heard(AT) and kept.checked
    assert (kept.no_length, kept.not_found, kept.stretch, kept.unused) == (0, 0, 0, 0)


def test_a_word_with_no_length_or_longer_than_anyone_says_it_is_never_kept() -> None:
    piled, drawn = Word("sierra", 14.0, 14.0), Word("tango", 15.0, 40.0)
    kept = check(AT, [*heard(AT), piled, drawn])
    assert kept.words == heard(AT) and kept.no_length == 2


def test_a_run_timed_away_from_where_it_is_said_is_left_out() -> None:
    early = laid(PHRASES[5], 22.0)  # said at 40 s, timed 18 s early on silence
    kept = check([*AT, (PHRASES[5], 40.0)], [*heard(AT), *early])
    assert kept.words == heard(AT) and kept.not_found == len(early) and not kept.stretch


def test_a_run_found_far_below_the_clips_own_runs_is_left_out() -> None:
    faint = laid(PHRASES[5], 15.0)
    probs = sound(AT)
    probs[:, :] = np.maximum(probs, sound([(PHRASES[5], 15.0)], faint=FOUND + 0.1))
    kept = confirmed(probs, [*heard(AT), *faint], tokens)
    assert kept.words == heard(AT) and kept.not_found == len(faint)


def test_a_stretch_mostly_not_found_is_left_out_whole() -> None:
    right = laid(PHRASES[0], 60.0)
    wrong = [w for k in (1, 2, 3) for w in laid(PHRASES[k], 60.0 + 3.0 * k)]  # said elsewhere
    first = AT[:3]
    kept = check([*first, (PHRASES[0], 60.0)], [*heard(first), *right, *wrong])
    assert kept.words == heard(first) and kept.stretch == len(right) + len(wrong)


def test_when_hardly_any_is_found_none_is_used() -> None:
    timed = [w for text, start in AT for w in laid(text, start + 50.0)]
    kept = check(AT, [*timed, Word("sierra", 3.0, 3.0)])
    assert kept.words == [] and kept.unused == len(timed) and kept.no_length == 1


def test_words_with_no_letters_to_look_for_are_used_as_before() -> None:
    words = [Word("٣", 1.0, 1.3), Word("٤", 1.4, 1.7), Word("٥", 2.0, 2.0)]
    kept = check(AT, words)
    assert not kept.checked and kept.words == words[:2] and kept.no_length == 1


def test_a_short_run_goes_with_the_runs_either_side_of_it() -> None:
    between = Word("ok", 2.95, 3.05)  # between two runs found
    lost = Word("ok", 17.8, 17.9)  # between two runs timed on silence
    wrong = [*laid(PHRASES[5], 16.0), *laid(PHRASES[1], 18.7)]
    kept = check(AT, sorted([*heard(AT), between, lost, *wrong], key=lambda w: w.start))
    assert between in kept.words and lost not in kept.words
    assert not set(map(id, wrong)) & set(map(id, kept.words))
