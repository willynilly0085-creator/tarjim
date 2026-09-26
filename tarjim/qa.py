from dataclasses import dataclass

from tarjim.lines import display_lines
from tarjim.models import Cue
from tarjim.rules import DEFAULT_RULES, Rules

TOLERANCE = 1e-3


@dataclass(frozen=True)
class Issue:
    number: int
    kind: str
    detail: str


def check(cues: list[Cue], rules: Rules = DEFAULT_RULES) -> list[Issue]:
    issues: list[Issue] = []
    for number, cue in enumerate(cues, start=1):
        issues += cue_issues(number, cue, rules)
        if number < len(cues) and cue.end > cues[number].start - rules.min_gap + TOLERANCE:
            issues.append(Issue(number, "overlap", f"ends {cue.end:.2f}"))
    return issues


def cue_issues(number: int, cue: Cue, rules: Rules) -> list[Issue]:
    issues = []
    lines = display_lines(cue.text, rules) if cue.text else []
    if any(len(line) > rules.line_chars for line in lines):
        issues.append(Issue(number, "line_length", str([len(x) for x in lines])))
    if len(lines) > rules.max_lines:
        issues.append(Issue(number, "too_many_lines", str(len(lines))))
    cps = len(cue.text) / max(cue.duration, TOLERANCE)
    if cue.text and cps > rules.reading_cps * 1.25:
        issues.append(Issue(number, "reading_speed", f"{cps:.0f} cps"))
    return issues
