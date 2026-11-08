"""Where the heard lines start from before they are timed: the pass the audio backs most, moved to
the times the words this computer heard back, with the kept fills still needed. Moved out of
listen/settle.py on 2026-11-08, unchanged, to make room there; settle.py still offers it."""
from dataclasses import dataclass

from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Fill, Heard
from tarjim.models import Word


def by_time(lines: list[Utterance]) -> list[Utterance]:
    return sorted(lines, key=lambda u: u.start)


@dataclass(frozen=True)
class Placed:
    own: list[Utterance]  # at the listener's own times
    moved: list[Utterance]  # at the times the audio backs
    fills: list[Fill]  # the kept fills still needed


def placed(heard: Heard, opinion: list[Word], duration: float) -> Placed:
    """The hearing the audio backs most, with what filled the stretches it left out on an earlier
    run, while the lines chosen now still leave them out (listen/fills.py)."""
    from tarjim.asr.anchor import anchor
    from tarjim.listen.fills import still_needed
    from tarjim.listen.recover import best_heard

    chosen = best_heard(heard.utterances, heard.passes, opinion)
    moved = anchor(chosen, opinion, duration)
    fills = still_needed(heard.added, moved)
    extra = [fill.line for fill in fills]
    return Placed(by_time([*chosen, *extra]), by_time([*moved, *extra]), fills)
