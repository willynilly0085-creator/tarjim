"""Every subscription is offered in setup, installed or not, and a failed install says why."""
import sys
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
    assert command == [sys.executable, "-P", "-m", "tarjim.engines.node_setup", "@openai/codex"]
    assert app_install.state("codex", False)["can_install"]
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


def test_the_first_node_install_takes_the_newest_lts_and_only_a_known_program(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.engines import node_release, node_setup

    made: list[Any] = []
    index = [{"version": "v24.22.1", "lts": "Krypton", "files": ["win-x64-zip"]}]
    monkeypatch.setattr(node_release, "ask_index", lambda: index)
    monkeypatch.setattr(node_release, "build", lambda *given: made.append(given))
    assert node_setup.main(["@openai/codex & calc"]) == 2 and made == []
    assert node_setup.main(["@openai/codex"]) == 0
    assert made == [("v24.22.1", ["@openai/codex"])]

    def refused(*_given: Any) -> None:
        raise node_release.Refused("node-v24.22.1-win-x64.zip does not match SHASUMS256.txt")

    monkeypatch.setattr(node_release, "build", refused)
    assert node_setup.main(["@github/copilot"]) == 1
    monkeypatch.setattr(node_release, "ask_index", lambda: [])
    assert node_setup.main(["@github/copilot"]) == 1


def test_npm_is_allowed_to_run_the_programs_own_install_script() -> None:
    """npm 12 skips install scripts; Claude Code's fetches its program (2026-10-31)."""
    from tarjim.engines.own_node import scripts_for

    assert scripts_for(["@anthropic-ai/claude-code"]) == "--allow-scripts=@anthropic-ai/claude-code"
    assert scripts_for(["@openai/codex@latest", "pkg@1.2"]) == "--allow-scripts=@openai/codex,pkg"
