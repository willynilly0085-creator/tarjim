from tarjim.lines import display_lines
from tarjim.models import Cue

MIN_STAGE = 0.4


def reveal_at(cue: Cue) -> float | None:
    if not cue.is_dialogue or len(display_lines(cue.text)) != len(cue.parts):
        return None
    moment = cue.parts[-1][0].start
    fits = cue.start + MIN_STAGE <= moment <= cue.end - MIN_STAGE
    return moment if fits else None
