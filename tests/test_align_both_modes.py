"""The aligner's tests, again in its tolerant mode (listen.aligner, 2026-11-09): as the mode is
measured on each clip (too few runs for prices keeps the strict reading), and with the star and
the skip forced on whatever the clip, so the tolerant path itself runs on every one of them."""
from collections.abc import Iterator

import pytest

from tarjim.asr import tolerated
from tarjim.asr.agree import FOUND
from tarjim.asr.costs import Calibration, Costs
from tests.test_align import *  # noqa: F403
from tests.test_align_split import *  # noqa: F403
from tests.test_emissions_once import *  # noqa: F403
from tests.test_emissions_once import hearing  # noqa: F401
from tests.test_overlap import *  # noqa: F403
from tests.test_sync_check import *  # noqa: F403


@pytest.fixture(autouse=True, params=["measured", "forced"])
def tolerant(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    monkeypatch.setenv("TARJIM_ALIGNER_MODE", tolerated.TOLERANT)
    if request.param == "forced":
        monkeypatch.setattr(tolerated, "measured",
                            lambda *_a: Calibration(Costs(star_delta=1.0), FOUND))
    yield str(request.param)
