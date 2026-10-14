"""Pairing is decided by the code the extension shows the person, never by a blind Allow."""
import pytest

from tarjim.server import pairing as pairing_module
from tarjim.server.pairing import LIMIT, Pairing

OURS = "chrome-extension://pbfjcnbdlokmgmldbkbmihnalfnhjjgp"
STRANGER = "chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def test_allowing_needs_the_code_the_extension_shows() -> None:
    pairing = Pairing()
    request = pairing.ask(OURS)
    assert request is not None
    wrong = "0000" if request.code != "0000" else "0001"
    assert not pairing.decide(request.id, True)
    assert not pairing.decide(request.id, True, wrong)
    assert pairing.claim(request.id, "TOKEN") == {"state": "pending"}
    assert pairing.decide(request.id, True, request.code)
    assert pairing.claim(request.id, "TOKEN") == {"state": "allowed", "token": "TOKEN"}


def test_the_strangers_code_does_not_allow_ours() -> None:
    pairing = Pairing()
    stranger, ours = pairing.ask(STRANGER), pairing.ask(OURS)
    assert stranger is not None and ours is not None
    assert not pairing.decide(stranger.id, True, ours.code)
    assert pairing.claim(stranger.id, "TOKEN") == {"state": "pending"}


def test_denying_needs_no_code() -> None:
    pairing = Pairing()
    request = pairing.ask(STRANGER)
    assert request is not None and pairing.decide(request.id, False)
    assert pairing.claim(request.id, "TOKEN") == {"state": "denied"}


def test_a_code_in_another_alphabet_is_just_wrong() -> None:
    pairing = Pairing()
    request = pairing.ask(OURS)
    assert request is not None and not pairing.decide(request.id, True, "٤٥٦٧")


def test_strangers_waiting_cannot_lock_another_extension_out() -> None:
    pairing = Pairing()
    for n in range(LIMIT * 2):
        assert pairing.ask(f"chrome-extension://{n:032d}") is not None
    assert pairing.ask(OURS) is not None


def test_an_extension_denied_again_and_again_must_wait() -> None:
    pairing = Pairing()
    for _ in range(LIMIT):
        request = pairing.ask(STRANGER)
        assert request is not None and pairing.decide(request.id, False)
    assert pairing.ask(STRANGER) is None
    assert pairing.ask(OURS) is not None


def test_two_waiting_requests_never_share_a_code(monkeypatch: pytest.MonkeyPatch) -> None:
    draws = iter([7, 7, 8])
    monkeypatch.setattr(pairing_module.secrets, "randbelow", lambda _n: next(draws))
    pairing = Pairing()
    first, second = pairing.ask(STRANGER), pairing.ask(OURS)
    assert first is not None and second is not None
    assert (first.code, second.code) == ("0007", "0008")
