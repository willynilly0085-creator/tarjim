from dataclasses import dataclass, replace

from tarjim.languages import Language


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

    @property
    def max_chars(self) -> int:
        return self.line_chars * self.max_lines

    def char_budget(self, duration: float) -> int:
        budget = int(self.reading_cps * duration)
        return max(self.min_budget, min(self.max_chars, budget))


DEFAULT_RULES = Rules()


def rules_for(target: Language) -> Rules:
    return replace(DEFAULT_RULES, line_chars=target.line_chars, reading_cps=target.reading_cps,
                   rtl=target.rtl, spaced=target.spaced)
