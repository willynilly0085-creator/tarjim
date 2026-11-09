"""How many letters one subtitle line holds on this picture (2026-11-08).

A language's line length is set for a wide picture. On a standing phone video the letters are
larger against a narrower picture: 42 Arabic letters at its font size (0.066 of 1080, 71 px)
need about 1250 px where about 920 px are free, so libass wrapped a subtitle into three or four
lines. The line is shortened for the picture's shape before cues are cut and translated, from
the drawn font size and a letter width kept on the wide side, so two lines always fit.
"""
from dataclasses import replace

from tarjim.prefs.model import Look
from tarjim.render.canvas import DEFAULT_LOOK, Canvas
from tarjim.rules import Rules

SHORTEST_LINE = 8


def fitted(rules: Rules, width: int, height: int, look: Look = DEFAULT_LOOK) -> Rules:
    """The rules with as many letters a line as fit, at the person's size, side margin and
    padding (2026-11-09)."""
    if width <= 0 or height <= 0:
        return rules  # a sound file: nothing is drawn
    canvas = Canvas.drawn((width, height), look, "")
    free = width - 2 * canvas.margin_h - 2 * canvas.shadow
    fits = int(free / (canvas.font_size * rules.char_em))
    line = max(SHORTEST_LINE, min(rules.line_chars, fits))
    if line == rules.line_chars:
        return rules
    source = max(SHORTEST_LINE, rules.max_source_chars * line // rules.line_chars)
    return replace(rules, line_chars=line, max_source_chars=source)
