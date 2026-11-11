"""A graphics-card failure never fails a job.

On 2026-11-10 five jobs in a row failed at the timing step with "CUDA out of memory ... 0 bytes
is free. Process 1816 has 17179869184.00 GiB memory in use" while the card held 1.4 of 16 GB: the
engine had run for hours, the computer had slept in between, and PyTorch's hold on the card was
broken, not full. Starting the engine again fixed it, and no person should have to know that.

So every step that runs a model on this computer goes through `survive`: a failure that is the
card's frees the models and runs the step again on the card (a card that was really full may
have room now); a second one marks the card as failed for this run, so `device.best_device()`
answers "cpu" and the models are built again on the processor, where the step runs a last time.
Slower, the same result. Never more than card, card, processor. A broken hold cannot be mended
inside the process, so the engine then starts again by itself once it is idle (server/renew.py)
and the next job has the card back.
"""
import re
from collections.abc import Callable
from typing import TypeVar

from tarjim import device, memory
from tarjim.job import checkpoint

Made = TypeVar("Made")
CARD_ERRORS = {"OutOfMemoryError", "AcceleratorError"}  # torch's own, by name: no import here
CARD_WORDS = re.compile(r"CUDA|cuDNN|device-side|unknown error", re.IGNORECASE)
SHOWN = 160
AGAIN = "{name}: the graphics card did not answer ({why}); models freed, trying it once more"
PROCESSOR = ("{name}: the graphics card failed again ({why}); this step runs on the processor "
             "(slower, same result) and the engine starts again when idle to get the card back")


def card_failure(error: BaseException) -> bool:
    """Out of memory on the card, or a CUDA / cuDNN error; nothing else."""
    if not isinstance(error, RuntimeError):
        return False
    names = {kind.__name__ for kind in type(error).__mro__}
    return bool(names & CARD_ERRORS) or bool(CARD_WORDS.search(str(error)))


def on_card() -> bool:
    return device.best_device() != "cpu"


def leave_card(name: str, why: str, last: bool) -> None:
    """Between two tries: the models leave the card, and a pause or cancel takes effect."""
    if last:
        device.CARD_FAILED.set()
    print((PROCESSOR if last else AGAIN).format(name=name, why=why), flush=True)
    memory.drop_models()
    checkpoint()


def survive(step: Callable[[], Made], name: str) -> Made:
    """What the step makes. The step builds its own model (shared_aligner() and the like) each
    time it is called, so a freed model is loaded again where best_device() now says."""
    for last in (False, True):
        try:
            return step()
        except RuntimeError as error:
            if not card_failure(error) or not on_card():
                raise
            why = " ".join(str(error).split())[:SHOWN]
        # outside the except: the error held the model's frames, and so its memory on the card
        leave_card(name, why, last)
    return step()
