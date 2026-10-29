"""A subscription program that hangs is stopped with everything it started, and a helper it
left behind never keeps tarjim waiting for its output (Codex runs node, which runs codex.exe)."""
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import psutil
import pytest

from tarjim.engines import antigravity, bounded, grok, sign_in, subscription, web

SCHEMA = {"type": "array", "items": {"type": "object"}}


def helper_script(folder: Path, parent_waits: bool) -> list[str]:
    """A program that starts a long-lived helper sharing its output, notes the helper's number,
    and then either hangs or finishes."""
    note = folder / "helper.pid"
    code = (
        "import subprocess, sys, time\n"
        "helper = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"open({str(note)!r}, 'w').write(str(helper.pid))\n"
        "print('started', flush=True)\n"
        f"time.sleep({60 if parent_waits else 0})\n")
    return [sys.executable, "-c", code]


def helper_of(folder: Path) -> int:
    return int((folder / "helper.pid").read_text())


def gone(pid: int) -> bool:
    try:
        return psutil.Process(pid).status() == psutil.STATUS_ZOMBIE
    except psutil.Error:
        return True


def test_a_hanging_program_is_stopped_with_its_helpers(tmp_path: Path) -> None:
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        bounded.bounded(helper_script(tmp_path, parent_waits=True), "", 3)
    assert time.monotonic() - started < 20
    assert gone(helper_of(tmp_path))


def test_a_helper_left_running_does_not_hold_the_answer(tmp_path: Path) -> None:
    started = time.monotonic()
    try:
        done = bounded.bounded(helper_script(tmp_path, parent_waits=False), "", 30)
        assert done.returncode == 0 and done.stdout.strip() == "started"
        assert time.monotonic() - started < 20
    finally:
        if not gone(helper_of(tmp_path)):
            psutil.Process(helper_of(tmp_path)).kill()


def test_the_prompt_reaches_the_program_and_its_words_come_back(tmp_path: Path) -> None:
    echo = [sys.executable, "-c", "import sys; sys.stdout.write(sys.stdin.read().upper())"]
    done = bounded.bounded(echo, "مرحبا hello\n" * 5000, 30, cwd=str(tmp_path))
    assert done.stdout == "مرحبا HELLO\n" * 5000


def test_a_subscription_that_ran_out_of_time_is_not_asked_again(
        monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def slow(command: list[str], _given: str, _seconds: float, **_options: Any) -> Any:
        calls.append(command)
        raise subprocess.TimeoutExpired(command, 900)

    monkeypatch.setattr(subscription, "bounded", slow)
    monkeypatch.setattr(antigravity, "launcher", lambda _name: ["agy"])
    with pytest.raises(web.TimedOut):
        antigravity.AntigravityAsker().twice("Translate.", None, SCHEMA, "")
    assert len(calls) == 1


@pytest.mark.parametrize("read", [grok.listing, antigravity.listing])
def test_a_model_listing_that_hangs_gives_nothing(
        monkeypatch: pytest.MonkeyPatch, read: Any) -> None:
    def slow(command: list[str], _given: str, seconds: float, **_options: Any) -> Any:
        raise subprocess.TimeoutExpired(command, seconds)

    monkeypatch.setattr(grok, "launcher", lambda _name: ["grok"])
    monkeypatch.setattr(antigravity, "launcher", lambda _name: ["agy"])
    monkeypatch.setattr(grok, "bounded", slow)
    monkeypatch.setattr(antigravity, "bounded", slow)
    assert read() == ""


def test_a_sign_in_check_that_hangs_says_signed_out(monkeypatch: pytest.MonkeyPatch) -> None:
    def slow(command: list[str], _given: str, seconds: float, **_options: Any) -> Any:
        raise subprocess.TimeoutExpired(command, seconds)

    monkeypatch.setattr(sign_in, "launcher", lambda name: [name])
    monkeypatch.setattr(sign_in, "bounded", slow)
    assert sign_in.signed_in("codex") is False
