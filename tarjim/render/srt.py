from tarjim.lines import display_lines
from tarjim.models import Cue
from tarjim.render.stages import reveal_at
from tarjim.render.timecode import srt_time
from tarjim.rules import DEFAULT_RULES, Rules

RLM = chr(0x200F)

Block = tuple[float, float, list[str]]


def render_srt(cues: list[Cue], rules: Rules = DEFAULT_RULES) -> str:
    blocks = [block for cue in cues if cue.text.strip() for block in stages(cue, rules)]
    return "\n".join(
        f"{number}\n{srt_time(start)} --> {srt_time(end)}\n" + "\n".join(lines) + "\n"
        for number, (start, end, lines) in enumerate(blocks, start=1))


def stages(cue: Cue, rules: Rules) -> list[Block]:
    mark = RLM if rules.rtl else ""
    lines = [f"{mark}{line}{mark}" for line in display_lines(cue.text, rules)]
    moment = reveal_at(cue)
    if moment is None:
        return [(cue.start, cue.end, lines)]
    return [(cue.start, moment, lines[:-1]), (moment, cue.end, lines)]
