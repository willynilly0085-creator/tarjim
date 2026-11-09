from tarjim.lines import display_lines, text_parts
from tarjim.models import Cue
from tarjim.rules import DEFAULT_RULES, Rules

MIN_STAGE = 0.4


def speaks_in_parts(cue: Cue, rules: Rules = DEFAULT_RULES) -> bool:
    """The translation kept the exchange's parts: one line for each person who speaks. One
    translation wrapped in two lines is not an exchange, even when the counts happen to match
    (2026-11-08: its second half was shown late and in the second speaker's colour)."""
    if not cue.is_dialogue or len(text_parts(cue.text)) != len(cue.parts):
        return False
    return len(display_lines(cue.text, rules)) == len(cue.parts)


def reveal_at(cue: Cue, rules: Rules = DEFAULT_RULES) -> float | None:
    """When the second speaker's line shows; None shows both lines at once, as the person
    can choose since 2026-11-09."""
    if not rules.staged or not speaks_in_parts(cue, rules):
        return None
    moment = cue.parts[-1][0].start
    fits = cue.start + MIN_STAGE <= moment <= cue.end - MIN_STAGE
    return moment if fits else None
