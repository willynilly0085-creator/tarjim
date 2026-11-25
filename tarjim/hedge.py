"""A second request when the first is slow, and whichever answers first (2026-11-25).

A selected text is waited for by a person. Measured on the owner's Mac that day, through the paid
Vertex key to gemini-3.8-flash: of six short sentences asked one after another, five answered in
1.7-2.7 s and one in 61 s, a single request that Google held and then answered 200 with nothing
wrong; an hour earlier two in a row took about 70 s each. No error and no retry was involved, so
nothing on tarjim's side could tell it was stuck. Past AFTER seconds the same request is sent once
more and the first answer is used; a failure of one still waits for the other. The one still
running is left to finish on its own and its answer dropped.
"""
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from contextvars import copy_context
from typing import TypeVar

AFTER = 4.0  # seconds: past the slow end of a normal answer (2.7 s measured)
Made = TypeVar("Made")


def hedged(ask: Callable[[], Made], after: float = AFTER) -> Made:
    """What ask gives, from a second call of it as well when the first takes over after."""
    pool = ThreadPoolExecutor(max_workers=2)
    try:
        calls = [pool.submit(copy_context().run, ask)]  # with this thread's settings (config.using)
        if not wait(calls, timeout=after).done:
            calls.append(pool.submit(copy_context().run, ask))
        return first_answer(calls)
    finally:
        pool.shutdown(wait=False)


def first_answer(calls: list["Future[Made]"]) -> Made:
    """The first call to answer; the error of the first to fail when none does."""
    pending, failed = set(calls), None
    while pending:
        done, pending = wait(pending, return_when=FIRST_COMPLETED)
        for call in done:
            if call.exception() is None:
                return call.result()
            failed = failed or call.exception()
    raise failed or RuntimeError("no call answered")
