"""A dropped download is tried again, and the last failure is the one reported."""
import pytest

from tarjim.retry import patiently


def test_a_download_that_drops_twice_still_finishes() -> None:
    seen: list[int] = []

    def action() -> None:
        seen.append(1)
        if len(seen) < 3:
            raise OSError("connection reset")

    patiently(action, tries=4, pause=0)
    assert len(seen) == 3


def test_a_download_that_never_works_reports_its_own_error() -> None:
    def action() -> None:
        raise OSError("no route to host")

    with pytest.raises(OSError, match="no route"):
        patiently(action, tries=2, pause=0)
