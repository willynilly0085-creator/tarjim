"""The settings of the job running now (2026-11-09).

pipeline.run puts the job's own settings here for as long as it runs, so the steps deep inside
it (how many passes a clip is heard in, how loud a dub's background is) read what the person
saw when they made the order, not what is saved by the time the step runs. Each pass, line and
piece thread copies the job's context (job.per_line, listen/merge.py), so it reads them too.
Outside a job (a test, a script) the defaults are read, with the old names from the
environment (TARJIM_VIDEO_MARK and the rest): never the person's saved file.
"""
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from tarjim.prefs.model import Prefs, resolve
from tarjim.prefs.store import from_environment

RUNNING: ContextVar[Prefs | None] = ContextVar("prefs", default=None)


def plain(target: str = "ar") -> Prefs:
    """The defaults for one language, with the old names set in the environment."""
    return resolve(from_environment(), {}, target)


def active(target: str = "ar") -> Prefs:
    return RUNNING.get() or plain(target)


@contextmanager
def using(prefs: Prefs) -> Iterator[Prefs]:
    token = RUNNING.set(prefs)
    try:
        yield prefs
    finally:
        RUNNING.reset(token)
