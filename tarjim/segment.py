from tarjim.breaks import SENTENCE_END, best_split
from tarjim.dialogue import Piece, merge_short, with_replies
from tarjim.fit import fit_timing
from tarjim.models import Cue, Word, join_words
from tarjim.rules import DEFAULT_RULES, Rules
from tarjim.speakers import who
from tarjim.tracks import tracks

EDGE = 0.05
MIN_SPLITTABLE = 2


def build_cues(words: list[Word], cuts: list[float], rules: Rules = DEFAULT_RULES) -> list[Cue]:
    """Words in time order on one track, replies said over a turn as parts of its subtitle,
    then each subtitle's time on screen (2026-11-08)."""
    main, replies = tracks(words, rules)
    blocks = split_blocks(main, cuts, rules)
    pieces = [piece for block in blocks for piece in split_long(block, rules)]
    return fit_timing(with_replies(merge_short(pieces, rules), replies, rules), rules, cuts)


def ends_sentence(word: Word) -> bool:
    return word.text.rstrip().endswith(SENTENCE_END)


def split_blocks(words: list[Word], cuts: list[float], rules: Rules) -> list[Piece]:
    labelled = any(word.speaker for word in words)
    cut_breaks = set() if labelled else snap_cuts(words, cuts, rules.cut_snap)
    between = cuts_between(words, cuts)
    blocks: list[Piece] = []
    for index, word in enumerate(words):
        at_cut = index in cut_breaks
        prev = blocks[-1].words[-1] if blocks else None
        changed = prev is not None and speaker_changed(prev, word, labelled, at_cut)
        if prev is None or changed or is_break(prev, word, at_cut, rules):
            blocks.append(Piece([], new_speaker=changed, after_cut=at_cut or index in between))
        blocks[-1].words.append(word)
    return blocks


def speaker_changed(prev: Word, word: Word, labelled: bool, at_cut: bool) -> bool:
    return who(prev.speaker) != who(word.speaker) if labelled else at_cut


def is_break(prev: Word, word: Word, at_cut: bool, rules: Rules) -> bool:
    """A shot change, a sentence's end, a long pause, or a turn said at the same time as the
    one before it (time going back), which is a subtitle of its own."""
    went_back = word.start < prev.start
    return at_cut or went_back or ends_sentence(prev) or word.start - prev.end >= rules.long_pause


def cuts_between(words: list[Word], cuts: list[float]) -> set[int]:
    return {i for cut in cuts if (i := gap_containing(words, cut)) is not None}


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
    head = Piece(block.words[:index], block.new_speaker, block.after_cut)
    tail = Piece(block.words[index:], new_speaker=False)
    return split_long(head, rules) + split_long(tail, rules)


def fits(words: list[Word], rules: Rules) -> bool:
    duration = words[-1].end - words[0].start
    chars = len(join_words(words))
    return duration <= rules.max_duration and chars <= rules.max_source_chars
