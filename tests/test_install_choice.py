"""Every subscription is offered in setup, installed or not, and a failed install says why."""
from pathlib import Path
from typing import Any

import pytest

from tarjim.engines import app_install

WEB = Path(__file__).resolve().parents[1] / "tarjim" / "web"


class Ended:
    def __init__(self, code: int) -> None:
        self.code = code

    def poll(self) -> int:
        return self.code


@pytest.fixture(autouse=True)
def own_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    monkeypatch.setattr(app_install, "HOME", tmp_path)
    app_install.running.clear()
    yield
    app_install.running.clear()


def test_a_failed_install_carries_what_the_installer_said() -> None:
    printed = "downloading\nERROR: no space left on device\nAt line:1 char:3\n+ irm x | iex\n"
    app_install.record("grok").write_text(printed, encoding="utf-8")
    app_install.running["grok"] = Ended(1)  # type: ignore[assignment]
    state = app_install.state("grok", found=False)
    assert state["install_failed"] and state["install_detail"] == "ERROR: no space left on device"


def test_an_install_that_ends_without_its_program_is_a_failure_with_a_reason() -> None:
    app_install.running["claude"] = Ended(0)  # type: ignore[assignment]
    state = app_install.state("claude", found=False)
    assert state["install_failed"] and "not found" in state["install_detail"]
    assert not app_install.state("claude", found=True)["install_failed"]


def test_nothing_is_reported_before_an_install_was_asked_for() -> None:
    state = app_install.state("antigravity", found=False)
    assert state["can_install"] and not state["installing"] and not state["install_failed"]
    assert state["install_detail"] == ""


def test_setup_offers_subscriptions_that_are_not_installed_and_connects_them_in_place() -> None:
    options = (WEB / "assistant_options.js").read_text(encoding="utf-8")
    assert "filter((a) => a.installed)" not in options and "needsInstall" in options
    plan = (WEB / "assistant_plan.js").read_text(encoding="utf-8")
    assert "connectBody(app, sub, ready, repaint)" in plan and "needInstall" in plan


def test_without_node_tarjim_brings_its_own_for_npm_programs(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from tarjim.engines import own_node, subscription

    monkeypatch.setattr(app_install, "npm", lambda: "")
    monkeypatch.setattr(own_node, "AVAILABLE", True)
    monkeypatch.setattr(own_node, "FOLDER", tmp_path / "node")
    command = app_install.command("codex")
    assert command[0] == "powershell" and "nodejs.org/dist" in command[-1]
    assert "@openai/codex" in command[-1] and app_install.state("codex", False)["can_install"]
    assert app_install.command("claude") == app_install.NATIVE["claude"]
    (tmp_path / "node" / "node_modules" / "codex").mkdir(parents=True)
    for name in ("npm.cmd", "node.exe", "node_modules/codex/run.js"):
        (tmp_path / "node" / name).write_text("", encoding="utf-8")
    assert app_install.command("copilot")[:4] == [own_node.npm(), "install", "-g", "--prefix"]
    shim = r'@"%dp0%\node.exe" "%dp0%\node_modules\codex\run.js" %*'
    (tmp_path / "node" / "codex.cmd").write_text(shim, encoding="utf-8")
    monkeypatch.setattr(subscription.programs, "find", lambda _name: None)
    found = subscription.launcher("codex")
    assert found[0] == own_node.node() and found[1].endswith("run.js")
