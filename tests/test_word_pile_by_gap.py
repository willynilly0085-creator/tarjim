"""A pile with squeezed words before it, right after a long gap (a Persian clip, 2026-10-31):
"و این نشست" 0.1 s apart at 89.6-89.8 s, then 33 words at 90.1 s, after a word that ends at
77.2 s. The words are spread back over 77.7-90.6 s; nothing is heard again, lost or doubled."""
from itertools import pairwise
from typing import Any

from tarjim.asr import align
from tarjim.listen.coverage import Hearing
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.novel import Again
from tarjim.listen.wordcover import recheck
from tarjim.models import Word

BEFORE = [Word(f"پیش{i}", 70.0 + 0.4 * i, 70.3 + 0.4 * i, "S1") for i in range(16)]
LAST = Word("گفت‌وگوئه.", 76.7, 77.2, "S1")
LEAD = [Word("و", 89.6, 89.62, "S1"), Word("این", 89.62, 89.72, "S1"),
        Word("نشست", 89.72, 89.82, "S1")]
PILE = [Word(f"تهران{i}", 90.1, 90.1, "S1") for i in range(33)]
AFTER = [Word(f"پس{i}", 90.7 + 0.4 * i, 91.0 + 0.4 * i, "S1") for i in range(8)]
WORDS = [*BEFORE, LAST, *LEAD, *PILE, *AFTER]
LINES = [Utterance(70.0, 77.3, "S1", " ".join(w.text for w in [*BEFORE, LAST])),
         Utterance(77.8, 94.3, "S1", " ".join(w.text for w in [*LEAD, *PILE, *AFTER]))]
LOCAL = [Word(f"محلی{i}", 78.0 + 0.85 * i, 78.4 + 0.85 * i, "S1") for i in range(13)]


class Timer:
    """Aligns the words of a line evenly over it, as an aligner that hears them would."""

    def __init__(self) -> None:
        self.lines: list[Utterance] = []

    def part(self, lines: list[Utterance]) -> list[Word]:
        self.lines.extend(lines)
        return [w for u in lines for w in align.proportional(u)]


def test_squeezed_words_and_a_pile_by_a_gap_are_spread_over_it(capsys: Any) -> None:
    asked: list[tuple[float, float]] = []

    def relisten(start: float, end: float) -> list[Utterance]:
        asked.append((start, end))
        return []

    hearing = Hearing(LINES, LOCAL, [(70.0, 94.0)])
    timer = Timer()
    checked = recheck(hearing, list(WORDS), timer, Again(relisten, "fakecloud", []))  # type: ignore[arg-type]
    log = capsys.readouterr().out
    assert "coverage: words gap 77.7-89.1 s" in log
    assert "re-timed 36 words into 77.7-90.6 s" in log
    assert asked == [] and checked.added == [] and checked.left == []
    assert [w.text for w in checked.words] == [w.text for w in WORDS]
    moved = checked.words[len(BEFORE) + 1:len(BEFORE) + 37]
    assert moved[0].start >= 77.7 and moved[-1].end <= 90.61
    assert all(b.start >= a.end - 1e-9 for a, b in pairwise(moved))
    assert checked.words[len(BEFORE) + 37:] == AFTER  # the words after it are left alone
