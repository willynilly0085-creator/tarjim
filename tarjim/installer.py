"""Install the tarjim engine for someone who only has the chat plugin, then start it.

Runs as its own hidden background process (standard library only) and records its progress in
~/.tarjim/install.json so the chat tools can report it.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("TARJIM_HOME", Path.home() / ".tarjim"))
STATE = HOME / "install.json"
LOG = HOME / "install.log"
CUDA_WHEELS = "https://download.pytorch.org/whl/cu128"
NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
DETACHED = 0x00000008 if sys.platform == "win32" else 0


def record(state: str, detail: str = "") -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"state": state, "detail": detail, "at": time.time()}),
                     encoding="utf-8")


def has_nvidia_card() -> bool:
    try:
        return subprocess.run(["nvidia-smi", "-L"], capture_output=True, timeout=10,
                              creationflags=NO_WINDOW, check=False).returncode == 0
    except OSError:
        return False


def install_command(uv: str, source: str) -> list[str]:
    command = [uv, "tool", "install", "--force", "--python", "3.11", f"tarjim[dub] @ {source}"]
    if has_nvidia_card():
        command += ["--index", CUDA_WHEELS, "--index-strategy", "unsafe-best-match"]
    return command


def tool_bin(uv: str) -> Path:
    out = subprocess.run([uv, "tool", "dir", "--bin"], capture_output=True, text=True,
                         creationflags=NO_WINDOW, check=True)
    return Path(out.stdout.strip())


def server_program(uv: str) -> str:
    name = "tarjim-serve.exe" if sys.platform == "win32" else "tarjim-serve"
    return str(tool_bin(uv) / name)


def start_detached(command: list[str], log: Path) -> None:
    with log.open("ab") as out:
        subprocess.Popen(command, stdout=out, stderr=out, stdin=subprocess.DEVNULL,
                         creationflags=NO_WINDOW | DETACHED,
                         start_new_session=sys.platform != "win32")


def main(source: str) -> int:
    uv = shutil.which("uv")
    if not uv:
        record("failed", "uv is missing: install it from https://docs.astral.sh/uv/")
        return 1
    record("installing", "downloading the engine and its models' libraries")
    with LOG.open("ab") as out:
        done = subprocess.run(install_command(uv, source), stdout=out, stderr=out,
                              creationflags=NO_WINDOW, check=False)
    if done.returncode != 0:
        record("failed", f"install failed, see {LOG}")
        return 1
    start_detached([server_program(uv)], HOME / "server.log")
    record("done", "the engine is installed and starting")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
