import unicodedata
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from tarjim.languages import Language

if TYPE_CHECKING:  # the settings import this module's letter widths
    from tarjim.prefs.model import Prefs

DASH_WIDTH = 2  # the "- " that opens each line of an exchange
# How wide a letter is drawn, in parts of the font size, kept on the wide side so two lines
# always fit (2026-11-08): Arabic measures about 0.42, Latin about 0.5; Chinese, Japanese and
# Korean letters are a full square.
NARROW_EM = 0.5
WIDE_EM = 1.0
WIDE = ("W", "F")


@dataclass(frozen=True)
class Rules:
    long_pause: float = 2.5
    cut_snap: float = 0.35
    min_readable: float = 0.9
    join_gap: float = 1.0
    cut_dialogue_span: float = 2.0
    max_duration: float = 6.0
    min_duration: float = 0.8
    min_gap: float = 0.083
    linger: float = 0.4
    max_source_chars: int = 84
    line_chars: int = 42
    max_lines: int = 2
    reading_cps: float = 17.0
    min_budget: int = 12
    rtl: bool = True
    spaced: bool = True
    char_em: float = NARROW_EM
    # Since 2026-11-09 from the person's settings (tarjim/prefs): how many people one subtitle
    # may hold (an exchange is two), the mark before each of their lines, and how much faster
    # than the reading speed a line may go before the report warns.
    max_speakers: int = 2
    dash: str = "- "
    warn_at: float = 1.25
    staged: bool = True  # an exchange's second line shows when its speaker starts

    @property
    def max_chars(self) -> int:
        return self.line_chars * self.max_lines

    @property
    def shortest(self) -> float:
        """The least time any subtitle is shown: both floors hold (2026-11-08)."""
        return max(self.min_duration, self.min_readable)

    @property
    def part_chars(self) -> int:
        """The source one part of an exchange may hold: each part is drawn on one line."""
        return self.max_source_chars // self.max_lines

    def char_budget(self, duration: float) -> int:
        budget = int(self.reading_cps * duration)
        return max(self.min_budget, min(self.max_chars, budget))

    def budgets(self, duration: float, parts: int) -> list[int]:
        """The characters each part may take. An exchange shows each part on a line of its own,
        so one long part would wrap onto a third line (2026-11-08)."""
        if parts <= 1:
            return [self.char_budget(duration)]
        share = max(self.min_budget, self.char_budget(duration) // parts)
        return [min(share, self.line_chars - DASH_WIDTH)] * parts


DEFAULT_RULES = Rules()


def letter_width(target: Language) -> float:
    """Wide when most letters of the language's own name are drawn full width."""
    letters = [ch for ch in target.native if ch.isalpha()]
    wide = sum(unicodedata.east_asian_width(ch) in WIDE for ch in letters)
    return WIDE_EM if letters and 2 * wide >= len(letters) else NARROW_EM


def rules_for(target: Language, prefs: "Prefs | None" = None) -> Rules:
    shaped = replace(DEFAULT_RULES, line_chars=target.line_chars,
                     reading_cps=target.reading_cps, rtl=target.rtl, spaced=target.spaced,
                     char_em=letter_width(target))
    return shaped if prefs is None else chosen(shaped, prefs)


def chosen(rules: Rules, prefs: "Prefs") -> Rules:
    """The language's rules with the person's settings (2026-11-09). A cue holds as much
    speech as its lines hold letters (the review of 2026-11-09): a shorter line, or one line
    instead of two, makes shorter cues, not more squeezed ones."""
    text, timing = prefs.text, prefs.timing
    lines = 1 if text.one_line else rules.max_lines
    source = rules.max_source_chars * text.line_chars * lines // (
        rules.line_chars * rules.max_lines)
    return replace(rules, line_chars=text.line_chars, reading_cps=text.reading_cps,
                   max_lines=lines, max_source_chars=max(1, source),
                   min_duration=timing.min_duration, max_duration=timing.max_duration,
                   linger=timing.linger, min_gap=timing.min_gap, long_pause=timing.long_pause,
                   join_gap=timing.join_gap, min_readable=timing.min_readable,
                   cut_snap=timing.cut_snap, cut_dialogue_span=timing.cut_dialogue_span,
                   max_speakers=2 if timing.dialogue_cues and lines > 1 else 1,
                   dash=prefs.look.dialogue_dash, warn_at=text.reading_warning,
                   staged=prefs.look.staged_reveal)
