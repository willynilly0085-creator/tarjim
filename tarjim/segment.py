from tarjim.dialogue import Piece, merge_short
from tarjim.models import Cue, Word
from tarjim.rules import DEFAULT_RULES, Rules

SENTENCE_END = (".", "?", "!", "؟")
SOFT_END = (",", "،", ";", "؛", ":")
MIN_SPAN = 1e-6
EDGE = 0.05
MIN_SPLITTABLE = 2


def build_cues(words: list[Word], cuts: list[float], rules: Rules = DEFAULT_RULES) -> list[Cue]:
    blocks = split_blocks(words, cuts, rules)
    pieces = [piece for block in blocks for piece in split_long(block, rules)]
    return fit_timing(merge_short(pieces, rules), rules)


def ends_sentence(word: Word) -> bool:
    return word.text.rstrip().endswith(SENTENCE_END)


def split_blocks(words: list[Word], cuts: list[float], rules: Rules) -> list[Piece]:
    cut_breaks = snap_cuts(words, cuts, rules.cut_snap)
    blocks: list[Piece] = []
    for index, word in enumerate(words):
        at_cut = index in cut_breaks
        if not blocks or is_break(blocks[-1].words[-1], word, at_cut, rules):
            blocks.append(Piece([], after_cut=at_cut))
        blocks[-1].words.append(word)
    return blocks


def is_break(prev: Word, word: Word, at_cut: bool, rules: Rules) -> bool:
    return at_cut or ends_sentence(prev) or word.start - prev.end >= rules.long_pause


def snap_cuts(words: list[Word], cuts: list[float], snap: float) -> set[int]:
    return {i for cut in cuts if (i := nearest_gap(words, cut, snap)) is not None}


def nearest_gap(words: list[Word], cut: float, snap: float) -> int | None:
    containing = gap_containing(words, cut)
    if containing is not None:
        return containing
    best, best_distance = None, snap
    for index in range(1, len(words)):
        middle = (words[index - 1].end + words[index].start) / 2
        distance = abs(middle - cut)
        if distance <= best_distance:
            best, best_distance = index, distance
    return best


def gap_containing(words: list[Word], cut: float) -> int | None:
    for index in range(1, len(words)):
        if words[index - 1].end - EDGE <= cut <= words[index].start + EDGE:
            return index
    return None


def split_long(block: Piece, rules: Rules) -> list[Piece]:
    if len(block.words) < MIN_SPLITTABLE or fits(block.words, rules):
        return [block]
    index = best_split(block.words)
    head = Piece(block.words[:index], after_cut=block.after_cut)
    tail = Piece(block.words[index:], after_cut=False)
    return split_long(head, rules) + split_long(tail, rules)


def fits(words: list[Word], rules: Rules) -> bool:
    duration = words[-1].end - words[0].start
    chars = len(" ".join(w.text for w in words))
    return duration <= rules.max_duration and chars <= rules.max_source_chars


def best_split(block: list[Word]) -> int:
    middle = (block[0].start + block[-1].end) / 2
    span = max(block[-1].end - block[0].start, MIN_SPAN)

    def score(index: int) -> float:
        prev, word = block[index - 1], block[index]
        text = prev.text.rstrip()
        bonus = 2.0 if text.endswith(SENTENCE_END) else 1.0 if text.endswith(SOFT_END) else 0.0
        off_center = abs((prev.end + word.start) / 2 - middle) / span
        return bonus + 2 * (word.start - prev.end) - off_center

    return max(range(1, len(block)), key=score)


def fit_timing(cues: list[Cue], rules: Rules) -> list[Cue]:
    for index, cue in enumerate(cues):
        has_next = index + 1 < len(cues)
        limit = cues[index + 1].start - rules.min_gap if has_next else float("inf")
        wanted = max(cue.end + rules.linger, cue.start + rules.min_duration)
        wanted = min(wanted, cue.start + rules.max_duration)
        cue.end = max(min(wanted, limit), cue.start + MIN_SPAN)
    return cues
