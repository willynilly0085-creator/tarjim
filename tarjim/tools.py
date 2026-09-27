import os
import threading
from dataclasses import dataclass, field
from pathlib import Path

from tarjim.config import setting

XTTS_REPO = "coqui/XTTS-v2"
XTTS_FOLDER = "tts/tts_models--multilingual--multi-dataset--xtts_v2"


@dataclass(frozen=True)
class Tool:
    id: str
    sources: tuple[str, ...]
    size_gb: float
    required: bool
    kind: str


TOOLS = [
    Tool("timing", ("MahmoudAshraf/mms-300m-1130-forced-aligner",), 1.3, True, "hub"),
    Tool("accuracy", ("Qwen/Qwen3-ASR-1.7B", "Qwen/Qwen3-ForcedAligner-0.6B"), 5.9, False, "hub"),
    Tool("dubbing", (XTTS_REPO,), 1.9, False, "voice"),
    Tool("local_translation", ("aya-expanse:8b",), 5.1, False, "ollama"),
]
BY_ID = {tool.id: tool for tool in TOOLS}


@dataclass
class Progress:
    state: str = "idle"
    detail: str = ""
    started: list[str] = field(default_factory=list)


def voice_folder() -> Path:
    home = Path(os.environ.get("TTS_HOME") or setting("models") or Path.home() / ".tarjim")
    return home / XTTS_FOLDER


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


def installed(tool: Tool) -> bool:
    if tool.kind == "voice":
        return (voice_folder() / "model.pth").exists()
    if tool.kind == "ollama":
        return all(ollama_ready(model) for model in tool.sources)
    return all(hub_ready(repo) for repo in tool.sources)


def fetch(tool: Tool) -> None:
    from huggingface_hub import snapshot_download

    if tool.kind == "voice":
        folder = voice_folder()
        snapshot_download(XTTS_REPO, local_dir=str(folder))
        (folder / "tos_agreed.txt").write_text("I have read, understood and agreed to the CPML.",
                                               encoding="utf-8")
    elif tool.kind == "ollama":
        from tarjim.engines.ollama import base_url
        from tarjim.engines.web import post

        for model in tool.sources:
            post("local", f"{base_url()}/api/pull", {}, json={"name": model, "stream": False})
    else:
        for repo in tool.sources:
            snapshot_download(repo)


class Shelf:
    def __init__(self) -> None:
        self.progress = {tool.id: Progress() for tool in TOOLS}
        self.lock = threading.Lock()

    def view(self) -> list[dict[str, object]]:
        return [{"id": t.id, "size_gb": t.size_gb, "required": t.required,
                 "installed": installed(t), "state": self.progress[t.id].state,
                 "detail": self.progress[t.id].detail} for t in TOOLS]

    def start(self, tool_id: str) -> bool:
        tool = BY_ID.get(tool_id)
        with self.lock:
            if tool is None or self.progress[tool_id].state == "downloading":
                return False
            self.progress[tool_id] = Progress("downloading")
        threading.Thread(target=self.run, args=(tool,), daemon=True).start()
        return True

    def run(self, tool: Tool) -> None:
        try:
            fetch(tool)
            self.progress[tool.id] = Progress("done")
        except Exception as error:
            self.progress[tool.id] = Progress("failed", str(error)[:200])
