"""Pairing is the person's Allow or Deny on tarjim's page (no code, the owner's choice), and
no extension can lock another out by asking again and again."""
import pytest

from tarjim.server import pairing as pairing_module
from tarjim.server.pairing import LIMIT, Pairing

OURS = "chrome-extension://pbfjcnbdlokmgmldbkbmihnalfnhjjgp"
STRANGER = "chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"


def test_the_persons_allow_connects_without_any_code() -> None:
    pairing = Pairing()
    request = pairing.ask(OURS)
    assert request is not None
    assert pairing.claim(request.id, "TOKEN") == {"state": "pending"}
    assert pairing.decide(request.id, True)
    assert pairing.claim(request.id, "TOKEN") == {"state": "allowed", "token": "TOKEN"}


def test_deny_refuses_the_request() -> None:
    pairing = Pairing()
    request = pairing.ask(STRANGER)
    assert request is not None and pairing.decide(request.id, False)
    assert pairing.claim(request.id, "TOKEN") == {"state": "denied"}


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
