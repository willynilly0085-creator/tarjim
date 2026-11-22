"""How many take tarjim from GitHub, for the owner's daily report (library_report.py, 2026-11-22).

GitHub keeps a repository's traffic for 14 days only, so each day's numbers are kept in
~/.tarjim/github-numbers.json and the report can speak of the time since counting began.
Clones made by tarjim's own checks on GitHub (each job of a workflow run checks the code out) are
told apart: on 2026-11-22 they were 158 of the fortnight's 405 clones. The install files attached
to each release (scripts/release_files.py: tarjim-windows.zip, and install.sh for macOS and
Linux) count new installs alone: updates come from the tag's archive, which GitHub does not
count. Read with the owner's gh.
"""
import json
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO = "willynilly0085-creator/tarjim"
KEPT = Path.home() / ".tarjim" / "github-numbers.json"
INSTALL_FILES = {"tarjim-windows.zip": "ويندوز", "install.sh": "ماك ولينكس"}
Days = dict[str, dict[str, int]]


def gh(path: str) -> Any:
    """GitHub's answer through the owner's gh (traffic needs the owner's sign-in); None if not."""
    found = shutil.which("gh")
    if not found:
        return None
    done = subprocess.run([found, "api", "--paginate", "--slurp", path], capture_output=True,
                          text=True, encoding="utf-8", timeout=120, check=False)
    if done.returncode:
        return None
    pages = json.loads(done.stdout or "[]")
    return pages[0] if len(pages) == 1 else pages


def check_clones(day: str) -> int:
    """Clones made that day by tarjim's own checks: one per job that ran."""
    pages = gh(f"repos/{REPO}/actions/runs?created={day}&per_page=100") or {}
    runs = [r for page in (pages if isinstance(pages, list) else [pages])
            for r in page.get("workflow_runs", [])]
    jobs = [gh(f"repos/{REPO}/actions/runs/{r['id']}/jobs?per_page=100") or {} for r in runs]
    return sum(1 for page in jobs for j in page.get("jobs", []) if j.get("conclusion") != "skipped")


def fresh(kept: Days, yesterday: str) -> Days:
    """GitHub's last 14 days over what was kept. Checks are counted again for yesterday and
    today (the report runs early in the day, before today's runs), once for older days."""
    clones = (gh(f"repos/{REPO}/traffic/clones") or {}).get("clones", [])
    views = {v["timestamp"][:10]: v for v in (gh(f"repos/{REPO}/traffic/views") or {}).get(
        "views", [])}
    days = dict(kept)
    for bucket in clones:
        day = bucket["timestamp"][:10]
        seen = views.get(day, {})
        checks = days.get(day, {}).get("checks")
        days[day] = {"clones": bucket["count"], "cloners": bucket["uniques"],
                     "visits": seen.get("count", 0), "visitors": seen.get("uniques", 0),
                     "checks": check_clones(day) if checks is None or day >= yesterday else checks}
    return days


def installs() -> dict[str, int]:
    """Downloads of each install file, all releases together, by the system it is for."""
    releases = gh(f"repos/{REPO}/releases?per_page=100") or []
    counted = dict.fromkeys(INSTALL_FILES.values(), 0)
    for asset in (a for r in releases for a in r.get("assets", []) if a["name"] in INSTALL_FILES):
        counted[INSTALL_FILES[asset["name"]]] += asset["download_count"]
    return counted


def lines(days: Days, yesterday: str, stars: int, installed: dict[str, int]) -> list[str]:
    """The report's section: people only, with GitHub's own checks taken out."""
    day = days.get(yesterday, {})
    people = sum(max(d["clones"] - d["checks"], 0) for d in days.values())
    since = min(days, default=yesterday)
    return ["تنزيلات ترجم من GitHub:",
            f"• أمس: {max(day.get('clones', 0) - day.get('checks', 0), 0)} تنزيل من غير فحوص "
            f"GitHub ({day.get('checks', 0)} من الفحوص)، و{day.get('visitors', 0)} زوار للصفحة",
            "• ملفات التثبيت من بدينا نعدّها: " + "، ".join(
                f"{system} {count}" for system, count in installed.items()),
            f"• من {since}: {people} تنزيل من غير فحوص GitHub",
            f"• النجوم: {stars}", ""]


def section() -> list[str]:
    """Read, kept for tomorrow, and said; nothing kept when GitHub or gh does not answer."""
    repository = gh(f"repos/{REPO}")
    if repository is None:
        return ["تنزيلات ترجم من GitHub: ما قدرنا نقراها اليوم (gh ما رد)", ""]
    try:
        kept: Days = json.loads(KEPT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        kept = {}
    yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
    days = fresh(kept, yesterday)
    KEPT.parent.mkdir(parents=True, exist_ok=True)
    KEPT.write_text(json.dumps(days, indent=1, sort_keys=True), encoding="utf-8")
    return lines(days, yesterday, repository.get("stargazers_count", 0), installs())
