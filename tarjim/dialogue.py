from dataclasses import dataclass, field

from tarjim.models import Cue, Word, join_words
from tarjim.rules import Rules

MAX_SPEAKERS = 2


@dataclass
class Piece:
    words: list[Word] = field(default_factory=list)
    new_speaker: bool = False
    after_cut: bool = False

    @property
    def span(self) -> float:
        return self.words[-1].end - self.words[0].start


def merge_short(pieces: list[Piece], rules: Rules) -> list[Cue]:
    cues: list[Cue] = []
    for index, piece in enumerate(pieces):
        following = pieces[index + 1] if index + 1 < len(pieces) else None
        if cues and should_join(cues[-1], piece, rules) and not closer_ahead(
                cues[-1], piece, following, rules):
            join(cues[-1], piece)
        else:
            cues.append(new_cue(piece))
    return cues


def closer_ahead(cue: Cue, piece: Piece, following: Piece | None, rules: Rules) -> bool:
    if following is None or following.after_cut or piece.span >= rules.min_readable:
        return False
    if cue.words[-1].end - cue.start < rules.min_readable:
        return False
    behind = piece.words[0].start - cue.words[-1].end
    ahead = following.words[0].start - piece.words[-1].end
    return ahead < behind and ahead <= rules.join_gap


def new_cue(piece: Piece) -> Cue:
    words = list(piece.words)
    return Cue(words[0].start, words[-1].end, words, parts=[list(words)])


def should_join(cue: Cue, piece: Piece, rules: Rules) -> bool:
    if piece.after_cut and piece.words[-1].end - cue.start > rules.cut_dialogue_span:
        return False
    cue_span = cue.words[-1].end - cue.start
    if min(cue_span, piece.span) >= rules.min_readable:
        return False
    gap = piece.words[0].start - cue.words[-1].end
    combined = piece.words[-1].end - cue.start
    chars = len(cue.source) + len(join_words(piece.words))
    within = gap <= rules.join_gap and combined <= rules.max_duration
    return within and chars <= rules.max_source_chars and room_for(cue, piece)


def room_for(cue: Cue, piece: Piece) -> bool:
    return not piece.new_speaker or len(cue.parts) < MAX_SPEAKERS


def join(cue: Cue, piece: Piece) -> None:
    if piece.new_speaker:
        cue.parts.append(list(piece.words))
    else:
        cue.parts[-1].extend(piece.words)
    cue.words.extend(piece.words)
    cue.end = piece.words[-1].end
