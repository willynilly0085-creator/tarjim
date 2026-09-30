"""The job's message as a checklist of every step, so the person sees what is done, what is
happening now and what is left, instead of waiting on a single word.

The steps follow the pipeline for the chosen result (pipeline.run and write_outputs), then the two
steps that bring the result to the phone.
"""
import time
from typing import Any

from tarjim.phone.words import result_name, say

DONE, NOW, LATER, STOPPED = "✓", "●", "○", "✕"
PHONE_STEPS = ("prepare", "send")
ENDED = ("failed", "cancelled")
MINUTE = 60


def plan(mode: str, link: bool) -> list[str]:
    steps = (["downloading"] if link else []) + ["hearing", "timing", "translating", "writing"]
    if mode != "srt":
        steps.append("burning")
    if mode.startswith("dub-"):
        steps.append("dubbing")
    return [*steps, *(["prepare"] if mode != "srt" else []), "send"]


def label(step: str) -> str:
    return say(f"phone_step_{step}") if step in PHONE_STEPS else say(f"stage_{step}")


def mark(index: int, at: int, stopped: bool) -> str:
    if index < at:
        return DONE
    if index > at:
        return LATER
    return STOPPED if stopped else NOW


def footer(view: dict[str, Any], step: str) -> str:
    if step == "sent":
        return say("phone_sent")
    if view["stage"] in ENDED or view["paused"] or view["stage"] == "queued":
        return say("stage_paused" if view["paused"] else f"stage_{view['stage']}")
    minutes = int((time.time() - float(view["created"])) // MINUTE)
    return say("phone_elapsed", min=minutes) if minutes else ""


def checklist(task: Any, step: str, note: str = "", stopped: bool = False) -> str:
    view = task.view()
    steps = plan(str(view["mode"]), bool(view["link"]))
    at = len(steps) if step == "sent" else steps.index(step) if step in steps else -1
    stopped = stopped or view["stage"] in ENDED
    lines = [str(view["title"]), result_name(str(view["mode"]))]
    for index, name in enumerate(steps):
        extra = f" ({note})" if index == at and note else ""
        lines.append(f"{mark(index, at, stopped)} {label(name)}{extra}")
    end = footer(view, step)
    return "\n".join([*lines, end] if end else lines)
