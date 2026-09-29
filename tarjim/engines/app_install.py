"""Install a subscription's program (Claude Code, Codex, Copilot) for the person, hidden, with npm.

Without Node.js there is no npm; the page then links to the Node.js download instead.
"""
import shutil
import subprocess
import sys

HIDDEN = 0x08000000 if sys.platform == "win32" else 0
PACKAGES = {"claude": "@anthropic-ai/claude-code", "codex": "@openai/codex",
            "copilot": "@github/copilot"}
running: dict[str, subprocess.Popen[bytes]] = {}


def npm() -> str:
    return shutil.which("npm.cmd") or shutil.which("npm") or ""


def start(provider: str) -> str:
    if provider not in PACKAGES:
        return "unknown"
    program = npm()
    if not program:
        return "no_node"
    if installing(provider):
        return "started"
    running[provider] = subprocess.Popen(
        [program, "install", "-g", PACKAGES[provider]], stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=HIDDEN)
    return "started"


def installing(provider: str) -> bool:
    process = running.get(provider)
    return process is not None and process.poll() is None


def failed(provider: str) -> bool:
    process = running.get(provider)
    return process is not None and process.poll() not in (None, 0)
