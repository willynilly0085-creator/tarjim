"""Install a subscription's program (Claude Code, Codex, Copilot) for the person, hidden, with npm.

Without Node.js there is no npm: Claude Code then uses its own installer, and the page links the
other programs to the Node.js download.
"""
import shutil
import subprocess
import sys
from pathlib import Path

HIDDEN = 0x08000000 if sys.platform == "win32" else 0
PACKAGES = {"claude": "@anthropic-ai/claude-code", "codex": "@openai/codex",
            "copilot": "@github/copilot"}
def native(address: str) -> list[str]:
    """The vendor's own installer: a PowerShell script on Windows, a shell one elsewhere."""
    if sys.platform == "win32":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                f"irm {address}.ps1 | iex"]
    return ["bash", "-c", f"curl -fsSL {address}.sh | bash"]


NATIVE = {"claude": native("https://claude.ai/install"), "grok": native("https://x.ai/cli/install")}
NATIVE_BIN = Path.home() / ".local" / "bin"
running: dict[str, subprocess.Popen[bytes]] = {}


def npm() -> str:
    return shutil.which("npm.cmd") or shutil.which("npm") or ""


def start(provider: str) -> str:
    if provider not in PACKAGES and provider not in NATIVE:
        return "unknown"
    program = npm() if provider in PACKAGES else ""
    if not program and provider not in NATIVE:
        return "no_node"
    if installing(provider):
        return "started"
    command = [program, "install", "-g", PACKAGES[provider]] if program else NATIVE[provider]
    running[provider] = subprocess.Popen(
        command, stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=HIDDEN)
    return "started"


def installing(provider: str) -> bool:
    process = running.get(provider)
    return process is not None and process.poll() is None


def failed(provider: str) -> bool:
    process = running.get(provider)
    return process is not None and process.poll() not in (None, 0)
