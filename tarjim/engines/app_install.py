"""Install a subscription's program for the person, hidden: the vendor's own installer where it
has one, npm otherwise.

Without Node.js there is no npm: tarjim then brings its own (see own_node), and only where it
cannot does the page link to the Node.js download.
"""
import subprocess
import sys
from pathlib import Path
from typing import Any

from tarjim.config import HOME
from tarjim.engines import own_node, programs

HIDDEN = 0x08000000 if sys.platform == "win32" else 0
PACKAGES = {"claude": "@anthropic-ai/claude-code", "codex": "@openai/codex",
            "copilot": "@github/copilot"}


def native(address: str) -> list[str]:
    """The vendor's own installer: a PowerShell script on Windows, a shell one elsewhere."""
    if sys.platform == "win32":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                f"irm {address}.ps1 | iex"]
    return ["bash", "-c", f"curl -fsSL {address}.sh | bash"]


NATIVE = {"claude": native("https://claude.ai/install"), "grok": native("https://x.ai/cli/install"),
          "antigravity": native("https://antigravity.google/cli/install")}
NATIVE_BIN = Path.home() / ".local" / "bin"
TRACE = ("At line", "+ ", "    + ")
running: dict[str, subprocess.Popen[bytes]] = {}


def npm() -> str:
    return programs.find("npm.cmd") or programs.find("npm") or ""


def start(provider: str) -> str:
    if provider not in PACKAGES and provider not in NATIVE:
        return "unknown"
    if not possible(provider):
        return "no_node"
    if installing(provider):
        return "started"
    with record(provider).open("wb") as output:
        running[provider] = subprocess.Popen(
            command(provider), stdin=subprocess.DEVNULL, env=own_node.environment(),
            stdout=output, stderr=subprocess.STDOUT, creationflags=HIDDEN)
    return "started"


def possible(provider: str) -> bool:
    return provider in NATIVE or bool(provider in PACKAGES and (npm() or own_node.AVAILABLE))


def command(provider: str) -> list[str]:
    """npm when the person has it, the vendor's installer next, tarjim's own Node.js last."""
    if provider in PACKAGES and npm():
        package = PACKAGES[provider]
        return [npm(), "install", "-g", own_node.scripts_for([package]), package]
    return NATIVE[provider] if provider in NATIVE else own_node.install(PACKAGES[provider])


def record(provider: str) -> Path:
    """What the installer printed, kept so a failure can show its real reason."""
    folder = HOME / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"install-{provider}.log"


def installing(provider: str) -> bool:
    process = running.get(provider)
    return process is not None and process.poll() is None


def failed(provider: str) -> bool:
    process = running.get(provider)
    return process is not None and process.poll() not in (None, 0)


def finished(provider: str) -> bool:
    process = running.get(provider)
    return process is not None and process.poll() is not None


def reason(provider: str) -> str:
    """The installer's last words, or that it ended without leaving its program behind."""
    from tarjim.server.evidence import evidence

    try:
        printed = record(provider).read_text(encoding="utf-8", errors="replace")
    except OSError:
        printed = ""
    lines = [line for line in printed.splitlines() if line.strip() and not line.startswith(TRACE)]
    return evidence(lines[-1]) if lines else "the installer ended and its program was not found"


def state(provider: str, found: bool) -> dict[str, Any]:
    """Where installing stands for the page: finished without its program counts as failed."""
    broken = failed(provider) or (finished(provider) and not found)
    return {"node": bool(npm()),
            "can_install": possible(provider),
            "installing": installing(provider), "install_failed": broken,
            "install_detail": reason(provider) if broken else ""}
