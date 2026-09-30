import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from tarjim.config import setting

VOICE_REPO = "openbmb/VoxCPM2"
DUPLICATE_WEIGHTS = ["*.bin"]


@dataclass(frozen=True)
class License:
    name: str
    url: str
    commercial: bool
    consent: bool = False


@dataclass(frozen=True)
class Tool:
    id: str
    sources: tuple[str, ...]
    size_gb: float
    required: bool
    kind: str
    license: License


MMS = License("CC-BY-NC-4.0", "https://huggingface.co/MahmoudAshraf/mms-300m-1130-forced-aligner",
              commercial=False)
QWEN = License("Apache-2.0", "https://huggingface.co/Qwen/Qwen3-ASR-1.7B", commercial=True)
APACHE = License("Apache-2.0", "https://huggingface.co/openbmb/VoxCPM2", commercial=True)
AYA = License("CC-BY-NC-4.0", "https://ollama.com/library/aya-expanse", commercial=False)
LGPL = License("LGPL-2.1", "https://ffmpeg.org/legal.html", commercial=True)
TOOLS = [
    Tool("ffmpeg", ("BtbN/FFmpeg-Builds",), 0.08, True, "ffmpeg", LGPL),
    Tool("timing", ("MahmoudAshraf/mms-300m-1130-forced-aligner",), 1.2, True, "hub", MMS),
    Tool("accuracy", ("Qwen/Qwen3-ASR-1.7B", "Qwen/Qwen3-ForcedAligner-0.6B"), 6.3, False, "hub",
         QWEN),
    Tool("dubbing", (VOICE_REPO,), 4.7, False, "voice", APACHE),
    Tool("local_translation", ("aya-expanse:8b",), 5.1, False, "ollama", AYA),
]
BY_ID = {tool.id: tool for tool in TOOLS}


@dataclass
class Progress:
    state: str = "idle"
    detail: str = ""
    started: list[str] = field(default_factory=list)


def hub_ready(repo: str) -> bool:
    from huggingface_hub import snapshot_download

    try:
        snapshot_download(repo, local_files_only=True)
    except Exception:
        return False
    return True


def ollama_ready(model: str) -> bool:
    import requests

    from tarjim.engines.ollama import base_url
    from tarjim.engines.web import OK

    try:
        reply = requests.get(f"{base_url()}/api/tags", timeout=5)
    except requests.RequestException:
        return False
    if reply.status_code != OK:
        return False
    return model in {m.get("name") for m in reply.json().get("models", [])}


def ffmpeg_ready() -> bool:
    import shutil

    chosen = setting("ffmpeg")
    return bool(chosen and Path(chosen).exists()) or bool(shutil.which("ffmpeg"))


def self_installs(tool: Tool) -> bool:
    """tarjim fetches ffmpeg on Windows only; elsewhere the package manager provides it."""
    return tool.kind != "ffmpeg" or sys.platform == "win32"


def listening_locally() -> bool:
    from tarjim.engines.choice import chosen

    return chosen("listen") == "local"


def installed(tool: Tool) -> bool:
    if tool.kind == "ffmpeg":
        return ffmpeg_ready()
    if tool.kind == "voice":
        from tarjim.dub.voice_setup import ready

        return ready() and hub_ready(VOICE_REPO)
    if tool.kind == "ollama":
        return all(ollama_ready(model) for model in tool.sources)
    return all(hub_ready(repo) for repo in tool.sources)


@contextmanager
def online() -> Iterator[None]:
    from huggingface_hub import constants

    before = constants.HF_HUB_OFFLINE
    constants.HF_HUB_OFFLINE = False
    try:
        yield
    finally:
        constants.HF_HUB_OFFLINE = before


def fetch(tool: Tool) -> None:
    with online():
        download(tool)


def download(tool: Tool) -> None:
    from huggingface_hub import snapshot_download

    if tool.kind == "ffmpeg":
        from tarjim.ffmpeg_setup import install_ffmpeg

        install_ffmpeg()
    elif tool.kind == "voice":
        from tarjim.dub.voice_setup import install

        install()
        snapshot_download(VOICE_REPO)
    elif tool.kind == "ollama":
        from tarjim.engines.ollama import base_url
        from tarjim.engines.web import post

        for model in tool.sources:
            post("local", f"{base_url()}/api/pull", {}, json={"name": model, "stream": False})
    else:
        for repo in tool.sources:
            snapshot_download(repo, ignore_patterns=DUPLICATE_WEIGHTS)


class Shelf:
    def __init__(self) -> None:
        self.progress = {tool.id: Progress() for tool in TOOLS}
        self.lock = threading.Lock()

    def view(self) -> list[dict[str, object]]:
        local = listening_locally()
        return [{"id": t.id, "size_gb": t.size_gb,
                 "required": t.required or (t.id == "accuracy" and local),
                 "installed": installed(t), "state": self.progress[t.id].state,
                 "detail": self.progress[t.id].detail, "license": t.license.name,
                 "license_url": t.license.url, "commercial": t.license.commercial,
                 "consent": t.license.consent, "manual": not self_installs(t)} for t in TOOLS]

    def start(self, tool_id: str, accepted: bool = False) -> str:
        tool = BY_ID.get(tool_id)
        if tool is None:
            return "unknown"
        if not self_installs(tool):
            return "manual"
        if tool.license.consent and not accepted:
            return "license"
        with self.lock:
            if self.progress[tool_id].state == "downloading":
                return "busy"
            self.progress[tool_id] = Progress("downloading")
        threading.Thread(target=self.run, args=(tool,), daemon=True).start()
        return "started"

    def run(self, tool: Tool) -> None:
        try:
            fetch(tool)
            self.progress[tool.id] = Progress("done")
        except Exception as error:
            self.progress[tool.id] = Progress("failed", str(error)[:200])
