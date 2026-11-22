"""The owner's daily report says how many take tarjim from GitHub, with GitHub's own checks taken
out and each day kept past GitHub's 14 days (scripts/github_numbers.py, 2026-11-22)."""
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("github_numbers",
                                                  ROOT / "scripts" / "github_numbers.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


numbers = load()
REPO = numbers.REPO


def answers(calls: list[str]) -> Any:
    table = {
        f"repos/{REPO}/traffic/clones": {"clones": [
            {"timestamp": "2026-11-20T00:00:00Z", "count": 49, "uniques": 18},
            {"timestamp": "2026-11-21T00:00:00Z", "count": 29, "uniques": 16}]},
        f"repos/{REPO}/traffic/views": {"views": [
            {"timestamp": "2026-11-21T00:00:00Z", "count": 3, "uniques": 2}]},
        f"repos/{REPO}/actions/runs?created=2026-11-20&per_page=100": {
            "workflow_runs": [{"id": 1}]},
        f"repos/{REPO}/actions/runs?created=2026-11-21&per_page=100": {"workflow_runs": []},
        f"repos/{REPO}/actions/runs/1/jobs?per_page=100": {"jobs": [
            {"conclusion": "success"}, {"conclusion": "skipped"}, {"conclusion": "failure"}]},
    }

    def gh(path: str) -> Any:
        calls.append(path)
        return table.get(path)
    return gh


def test_each_day_is_kept_and_a_past_days_checks_are_counted_once(
        monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(numbers, "gh", answers(calls))
    older = {"2026-11-01": {"clones": 9, "cloners": 3, "visits": 1, "visitors": 1, "checks": 4}}
    days = numbers.fresh(older, "2026-11-21")
    assert days["2026-11-01"] == older["2026-11-01"]  # gone from GitHub, kept here
    assert days["2026-11-20"] == {"clones": 49, "cloners": 18, "visits": 0, "visitors": 0,
                                  "checks": 2}  # the skipped job checked nothing out
    assert days["2026-11-21"]["visitors"] == 2
    calls.clear()
    numbers.fresh(days, "2026-11-22")
    assert not any("created=2026-11-20" in call for call in calls)


def test_the_report_counts_people_without_githubs_own_checks() -> None:
    days = {"2026-11-20": {"clones": 49, "cloners": 18, "visits": 0, "visitors": 0, "checks": 18},
            "2026-11-21": {"clones": 29, "cloners": 16, "visits": 3, "visitors": 2, "checks": 1}}
    said = "\n".join(numbers.lines(days, "2026-11-21", stars=1,
                                   installed={"ويندوز": 4, "ماك ولينكس": 2}))
    assert "أمس: 28 تنزيل من غير فحوص GitHub (1 من الفحوص)، و2 زوار للصفحة" in said
    assert "من 2026-11-20: 59 تنزيل" in said
    assert "ملفات التثبيت من بدينا نعدّها: ويندوز 4، ماك ولينكس 2" in said and "النجوم: 1" in said


def test_nothing_is_kept_or_said_as_numbers_when_gh_does_not_answer(
        monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(numbers, "gh", lambda _path: None)
    monkeypatch.setattr(numbers, "KEPT", tmp_path / "kept.json")
    assert "ما قدرنا" in numbers.section()[0]
    assert not (tmp_path / "kept.json").exists()


def test_installs_are_counted_by_system_over_every_release(
        monkeypatch: pytest.MonkeyPatch) -> None:
    releases = [{"assets": [{"name": "tarjim-windows.zip", "download_count": 3},
                            {"name": "install.sh", "download_count": 5},
                            {"name": "tarjim-firefox.xpi", "download_count": 9}]},
                {"assets": [{"name": "tarjim-windows.zip", "download_count": 1}]}]
    monkeypatch.setattr(numbers, "gh", lambda _path: releases)
    assert numbers.installs() == {"ويندوز": 4, "ماك ولينكس": 5}
