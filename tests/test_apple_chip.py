"""On a Mac with an Apple chip the models run on the chip's graphics (tarjim/device.py)."""
import pytest

from tarjim import card, device


@pytest.fixture(autouse=True)
def fresh() -> None:
    device.CARD_FAILED.clear()


def test_an_apple_chip_is_used_when_there_is_no_nvidia_card(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(device, "card_present", lambda: False)
    monkeypatch.setattr(device, "apple_present", lambda: True)
    assert device.best_device() == "mps"


def test_an_nvidia_card_comes_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(device, "card_present", lambda: True)
    monkeypatch.setattr(device, "apple_present", lambda: True)
    assert device.best_device() == "cuda:0"


def test_a_chip_that_failed_twice_hands_over_to_the_processor(
        monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(device, "card_present", lambda: False)
    monkeypatch.setattr(device, "apple_present", lambda: True)
    device.CARD_FAILED.set()
    assert device.best_device() == "cpu"
    device.CARD_FAILED.clear()


def test_the_chip_runs_at_full_precision() -> None:
    import torch

    # measured 2026-11-25 on an M5 Ultra: float32 gave the processor's words and times to the
    # millisecond; bfloat16 moved 393 of 963 listened words by more than 100 ms
    assert device.precision("mps", torch.bfloat16) is torch.float32
    assert device.precision("cuda:0", torch.bfloat16) is torch.bfloat16


def test_a_metal_failure_counts_as_the_card_s() -> None:
    assert card.card_failure(RuntimeError("MPS backend out of memory (MPS allocated: 9 GB)"))
    assert not card.card_failure(RuntimeError("the sample rate is not 16000"))


def test_the_fallback_for_metal_is_on_before_pytorch_loads() -> None:
    import os

    import tarjim  # noqa: F401

    assert os.environ.get("PYTORCH_ENABLE_MPS_FALLBACK") == "1"


def test_the_setup_page_counts_what_macos_lets_the_graphics_use() -> None:
    from types import SimpleNamespace

    from tarjim.system import GIB, apple_graphics

    torch = SimpleNamespace(mps=SimpleNamespace(recommended_max_memory=lambda: 5.3 * GIB))
    found = apple_graphics(torch)
    assert found["memory_gb"] == 5.3 and found["usable"] is True
    assert str(found["name"]).endswith("GPU")
