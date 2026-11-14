"""Other ways a job could pick the lines whose hearing it doubts, tried on runs already made:
each rule's list against the lines with a word not said (score.py) and against the sentences
the judge found not right because of the hearing (judge.py). Nothing is run again.

    python rules.py <label> [label ...]
"""
import json
import sys
from collections import Counter
from collections.abc import Callable
from typing import Any

from paths import CLIPS, RUNS, prepare

prepare()

from score import Scored  # noqa: E402

from tarjim.breaks import SENTENCE_END  # noqa: E402
from tarjim.models import Word  # noqa: E402

Row = dict[str, Any]
PASSES = 3  # the passes each clip of the bench was heard in
Rule = Callable[[list[Word]], bool]
OPENING = "\"'“‘«([¿¡-"
CLOSING = "\"'”’»)]"


def weighty(words: list[Word], k: int) -> bool:
    """A number, or a name: a capital that opens neither the line nor a sentence, and is not
    the English "I"."""
    text = words[k].text.lstrip(OPENING)
    if any(ch.isdigit() for ch in text):
        return True
    opens = k == 0 or words[k - 1].text.rstrip(CLOSING).endswith(SENTENCE_END)
    myself = text == "I" or text[:2] in ("I'", "I’")
    return text[:1].isupper() and not opens and not myself


def hearings(word: Word) -> int:
    return (word.backed or 0) + bool(word.local)


def told(words: list[Word]) -> list[int]:
    return [k for k, w in enumerate(words) if w.backed is not None or w.local is not None]


def now(words: list[Word]) -> bool:
    """tarjim/doubts.hearing_of as it first was: fewer than two hearings, a third or a name."""
    lone = [k for k in told(words) if hearings(words[k]) < 2]  # noqa: PLR2004
    much = len(lone) * 3 >= len(told(words))
    return bool(lone) and (much or any(weighty(words, k) for k in lone))


def any_alone(words: list[Word]) -> bool:
    return any(hearings(words[k]) < 2 for k in told(words))  # noqa: PLR2004


def not_all(words: list[Word]) -> bool:
    """A word some pass did not write."""
    return any((words[k].backed or 0) < PASSES for k in told(words))


def name_not_all(words: list[Word]) -> bool:
    return now(words) or any((words[k].backed or 0) < PASSES and weighty(words, k)
                             for k in told(words))


def long_not_all(words: list[Word]) -> bool:
    """A word of five letters or more some pass did not write, and the local listener neither."""
    return now(words) or any((words[k].backed or 0) < PASSES and not words[k].local
                             and len(words[k].text) >= 5 for k in told(words))  # noqa: PLR2004


RULES: dict[str, Rule] = {"now": now, "any word on one hearing": any_alone,
                          "any word a pass did not write": not_all,
                          "now + a name a pass did not write": name_not_all,
                          "now + a long word a pass and the local did not write": long_not_all}


def tally(flagged: bool, wrong: bool, counts: Counter[str]) -> None:
    counts[("t" if flagged == wrong else "f") + ("p" if flagged else "n")] += 1


def clip_rows(label: str, clip: str) -> tuple[Scored, list[Row]]:
    truth = json.loads((CLIPS / clip / "truth.json").read_text(encoding="utf-8"))
    result = json.loads((RUNS / label / clip / "result.json").read_text(encoding="utf-8"))
    meaning = json.loads((RUNS / label / clip / "meaning.json").read_text(encoding="utf-8"))
    return Scored(truth, result), meaning


def tried(rule: Rule, clip: tuple[Scored, list[Row]], found: tuple[Counter[str], ...]) -> None:
    """One rule's list for one clip, counted against the lines and the sentences at fault."""
    (one, meaning), (lines, sentences) = clip, found
    wrong, cues = one.wrong_lines(), one.result["cues"]
    listed = {c for c, cue in enumerate(cues) if rule([Word(**word) for word in cue["words"]])}
    for c in range(len(cues)):
        tally(c in listed, c in wrong, lines)
    for row in meaning:
        bad = row["meaning"] != "right" and row.get("cause") == "hearing"
        tally(bool(listed & {n - 1 for n in row["lines"]}), bad, sentences)


def main() -> None:
    lines = {name: Counter[str]() for name in RULES}
    sentences = {name: Counter[str]() for name in RULES}
    folders = [p for label in sys.argv[1:] for p in sorted((RUNS / label).iterdir())
               if (p / "meaning.json").exists()]
    for folder in folders:
        clip = clip_rows(folder.parent.name, folder.name)
        for name, rule in RULES.items():
            tried(rule, clip, (lines[name], sentences[name]))
    for name in RULES:
        line, sentence = lines[name], sentences[name]
        listed, faulted = line["tp"] + line["fp"], sentence["tp"] + sentence["fn"]
        print(f"{name:55} lines: lists {listed:3}, {line['tp']:3} wrong, misses {line['fn']:3} "
              f"| sentences faulted for hearing: lists {sentence['tp'] + sentence['fp']:3}, "
              f"catches {sentence['tp']:2} of {faulted:2}")


if __name__ == "__main__":
    main()
