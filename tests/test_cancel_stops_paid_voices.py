"""A cancelled dub stops asking the paid voice service for the lines not yet started."""
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from tarjim.job import CHECKPOINT, per_line
from tarjim.server.jobs import Stopped


def test_lines_after_a_cancel_are_never_sent() -> None:
    cancelled = threading.Event()
    sent: list[int] = []

    def guard() -> None:
        if cancelled.is_set():
            raise Stopped()

    def speak(line: int) -> int:
        sent.append(line)
        if line == 2:
            cancelled.set()  # the person pressed Cancel while line 2 was spoken
        return line

    token = CHECKPOINT.set(guard)
    try:
        with pytest.raises(Stopped), ThreadPoolExecutor(max_workers=1) as pool:
            list(pool.map(per_line(speak), range(10)))
    finally:
        CHECKPOINT.reset(token)
    assert sent == [0, 1, 2]


def test_without_a_cancel_every_line_is_spoken() -> None:
    with ThreadPoolExecutor(max_workers=3) as pool:
        assert list(pool.map(per_line(lambda line: line * 2), range(6))) == [0, 2, 4, 6, 8, 10]
