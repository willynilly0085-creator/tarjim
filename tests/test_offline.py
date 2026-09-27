import os

import pytest

from tarjim import config, tools


def test_models_load_offline_and_downloads_open_the_internet_only_while_they_run(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from huggingface_hub import constants

    for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"):
        monkeypatch.delenv(name, raising=False)
    config.prepare_environment()
    assert os.environ["HF_HUB_OFFLINE"] == "1" and os.environ["HF_HUB_DISABLE_TELEMETRY"] == "1"
    monkeypatch.setattr(constants, "HF_HUB_OFFLINE", True)
    seen: list[bool] = []
    monkeypatch.setattr(tools, "download", lambda _tool: seen.append(constants.HF_HUB_OFFLINE))
    tools.fetch(tools.TOOLS[0])
    assert seen == [False] and constants.HF_HUB_OFFLINE is True
