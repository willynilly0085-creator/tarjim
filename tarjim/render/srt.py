from tarjim.lines import display_lines
from tarjim.models import Cue
from tarjim.render.timecode import srt_time

RLM = chr(0x200F)


def render_srt(cues: list[Cue]) -> str:
    blocks = []
    for number, cue in enumerate((c for c in cues if c.text.strip()), start=1):
        lines = "\n".join(f"{RLM}{line}{RLM}" for line in display_lines(cue.text))
        blocks.append(f"{number}\n{srt_time(cue.start)} --> {srt_time(cue.end)}\n{lines}\n")
    return "\n".join(blocks)
