"""A short daily report, in Arabic, on everything tarjim depends on, sent to the owner's phone bot.

Run by the owner's scheduled task (see scripts/windows/library-report.cmd); nothing here runs for
people who use tarjim. It reads only public release data and the versions installed here:
known vulnerabilities in the tested Python libraries, how many of them have newer releases,
yt-dlp, Node.js, ffmpeg, Python 3.11, the subscription programs, and the last GitHub check.
    python -P scripts/library_report.py            send it
    python -P scripts/library_report.py --print    show it here instead
"""
import json
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tarjim.config import setting  # noqa: E402

PINS = ROOT / "tarjim" / "constraints.txt"
KNOWN = ROOT / ".github" / "audit-known.txt"
PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s;]+)")
NPM = {"Claude Code": "@anthropic-ai/claude-code", "Codex": "@openai/codex",
       "Copilot": "@github/copilot"}
TIMEOUT = 20


def run(*command: str) -> str:
    found = shutil.which(command[0])
    if not found:
        return ""
    done = subprocess.run([found, *command[1:]], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=300, check=False)
    return done.stdout


def numbers(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", version)[:4])


def pypi(name: str) -> str:
    try:
        return str(requests.get(f"https://pypi.org/pypi/{name}/json", timeout=TIMEOUT)
                   .json()["info"]["version"])
    except (requests.RequestException, ValueError, KeyError):
        return ""


def vulnerabilities() -> list[str]:
    report = json.loads(run("uvx", "--quiet", "pip-audit", "--disable-pip", "--no-deps",
                            "--progress-spinner", "off", "-f", "json", "-r", str(PINS)) or "{}")
    accepted = set(re.findall(r"^([A-Z][A-Z0-9-]+) ", KNOWN.read_text(encoding="utf-8"), re.M))
    found = {(d["name"], d["version"], v["id"], ",".join(v.get("fix_versions") or []))
             for d in report.get("dependencies", []) for v in d.get("vulns", [])}
    return [f"{name} {version}: {vid} (الإصلاح {fix or 'غير موجود'})"
            for name, version, vid, fix in sorted(found) if vid not in accepted]


def outdated() -> list[str]:
    pins = [m.groups() for line in PINS.read_text(encoding="utf-8").splitlines()
            if (m := PIN.match(line))]
    with ThreadPoolExecutor(max_workers=16) as pool:
        newest = list(pool.map(pypi, [name for name, _ in pins]))
    return [f"{name} {have} ← {new}" for (name, have), new in zip(pins, newest, strict=True)
            if new and numbers(new) > numbers(have)]


def node() -> str:
    releases = requests.get("https://nodejs.org/dist/index.json", timeout=TIMEOUT).json()
    lts = next(r for r in releases if r["lts"])
    mine = run("node", "--version").strip()
    own = Path.home() / ".tarjim" / "node" / "node.exe"
    theirs = run(str(own), "--version").strip() if own.is_file() else "غير مركّب"
    state = "محدّث" if mine == lts["version"] else f"عندك {mine or 'غير مركّب'}"
    return f"Node.js: آخر نسخة {lts['version']} ({state}، ونسخة ترجم {theirs})"


def ffmpeg() -> str:
    tool = setting("ffmpeg") or shutil.which("ffmpeg") or ""
    line = run(tool, "-version").splitlines()[:1] if tool else []
    latest = requests.get("https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest",
                          timeout=TIMEOUT).json().get("published_at", "")[:10]
    return f"ffmpeg: عندك {line[0].split()[2] if line else 'غير معروف'}، وآخر بناء {latest}"


def python() -> str:
    listing = run("uv", "python", "list", "3.11", "--only-downloads", "--output-format", "json")
    offered = [v["version"] for v in json.loads(listing or "[]")]
    newest = max(offered, key=numbers, default="")
    here = ".".join(map(str, sys.version_info[:3]))
    newer = f"، وفيه {newest}" if newest and newest != here else " (محدّث)"
    return f"بايثون 3.11: عندك {here}{newer}"


def programs() -> list[str]:
    installed = run("npm", "ls", "-g", "--depth=0", "--json")
    have = json.loads(installed or "{}").get("dependencies", {})
    lines = []
    for label, package in NPM.items():
        latest = run("npm", "view", package, "version").strip()
        mine = have.get(package, {}).get("version", "")
        if latest and mine and numbers(latest) > numbers(mine):
            lines.append(f"{label}: عندك {mine}، وفيه {latest}")
    return lines


RUNS = ("https://api.github.com/repos/willynilly0085-creator/tarjim/actions/workflows/ci.yml/runs"
        "?branch=master&per_page=1")
STATES = {"success": "ناجح", "failure": "فاشل", "cancelled": "انلغى", "in_progress": "شغّال الحين",
          "queued": "ينتظر دوره"}


def checks() -> str:
    """Asked of GitHub's public API, not of gh: the scheduled task runs outside the Claude app,
    where gh was never signed in (its sign-in sits in the app's own copy of AppData), so gh
    answered nothing and the line said "unknown" every morning."""
    try:
        runs = requests.get(RUNS, timeout=TIMEOUT).json().get("workflow_runs") or [{}]
    except (requests.RequestException, ValueError):
        runs = [{}]
    state = runs[0].get("conclusion") or runs[0].get("status") or ""
    return "فحص GitHub: " + STATES.get(state, state or "غير معروف")


def section(title: str, lines: list[str], limit: int = 8) -> list[str]:
    if not lines:
        return []
    more = [f"… و{len(lines) - limit} غيرها"] if len(lines) > limit else []
    return [f"{title} ({len(lines)}):", *[f"• {line}" for line in lines[:limit]], *more, ""]


def compose() -> str:
    new_risks, behind, apps = vulnerabilities(), outdated(), programs()
    head = ("تقرير مكتبات ترجم اليومي", "")
    verdict = ["كل شي سليم: ما فيه ثغرة جديدة.", ""] if not new_risks else []
    body = [*section("ثغرات جديدة تحتاج تحديث", new_risks),
            *section("مكتبات لها نسخة أحدث (تنحدث مع الإصدار الجاي بعد الاختبار)", behind),
            *section("برامج الاشتراكات", apps)]
    status = [node(), ffmpeg(), python(), checks()]
    return "\n".join([*head, *verdict, *body, *status])


def send(text: str) -> None:
    from tarjim.phone.telegram import Bot

    token, chat = setting("telegram_token"), setting("phone_chat")
    if not token or not chat:
        raise SystemExit("phone bot not linked: link it in tarjim's Settings first")
    Bot(token).say(int(chat), text[:4000])


def main(argv: list[str]) -> int:
    """Run without a window by the scheduled task, a failure is kept in ~/.tarjim's log."""
    try:
        text = compose()
        if "--print" not in argv:
            send(text)
            return 0
    except Exception as error:
        log = Path.home() / ".tarjim" / "library-report.log"
        with log.open("a", encoding="utf-8") as out:
            out.write(f"{type(error).__name__}: {error}\n")
        raise
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
