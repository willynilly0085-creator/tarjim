import json
import subprocess
from typing import Any

import pytest

from tarjim.engines import sign_in


class FakeProcess:
    def __init__(self, command: list[str], **options: Any) -> None:
        self.command, self.options, self.sent = command, options, ""
        self.stdin = self

    def write(self, text: str) -> None:
        self.sent += text

    def flush(self) -> None:
        return None

    def poll(self) -> None:
        return None


@pytest.fixture
def started(monkeypatch: pytest.MonkeyPatch) -> list[FakeProcess]:
    made: list[FakeProcess] = []

    def popen(command: list[str], **options: Any) -> FakeProcess:
        made.append(FakeProcess(command, **options))
        return made[-1]

    monkeypatch.setattr(sign_in, "launcher", lambda name: [f"{name}.exe"])
    monkeypatch.setattr(sign_in.subprocess, "Popen", popen)
    sign_in.waiting.clear()
    return made


def test_claude_signs_in_through_the_browser_without_a_window(started: list[FakeProcess]) -> None:
    assert sign_in.start("claude") == "browser"
    assert started[0].command == ["claude.exe", "auth", "login", "--claudeai"]
    assert started[0].options["creationflags"] == sign_in.HIDDEN


def test_a_code_from_the_sign_in_page_reaches_the_waiting_program(
        started: list[FakeProcess]) -> None:
    sign_in.start("claude")
    assert sign_in.send_code("claude", "abc123DEF#state-456")
    assert started[0].sent == "abc123DEF#state-456\n"
    assert not sign_in.send_code("claude", "bad code; rm -rf")
    assert not sign_in.send_code("codex", "abc123DEF#state-456")


def test_only_subscriptions_can_be_signed_into(started: list[FakeProcess]) -> None:
    assert sign_in.start("gemini") == ""
    assert sign_in.start("nonsense") == ""
    assert started == []


def test_sign_in_state_is_read_from_each_program(monkeypatch: pytest.MonkeyPatch) -> None:
    replies = {"claude": (0, json.dumps({"loggedIn": True})), "codex": (1, "Not logged in")}

    def run(command: list[str], **_options: Any) -> subprocess.CompletedProcess[str]:
        code, text = replies["claude" if "auth" in command else "codex"]
        return subprocess.CompletedProcess(command, code, text, "")

    monkeypatch.setattr(sign_in, "launcher", lambda name: [name])
    monkeypatch.setattr(sign_in.subprocess, "run", run)
    assert sign_in.signed_in("claude") is True
    assert sign_in.signed_in("codex") is False
