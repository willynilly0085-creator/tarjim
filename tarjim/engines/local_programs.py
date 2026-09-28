"""AI programs installed on this computer but not running yet: find them, list their models, and
start them without a window."""
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from tarjim.engines.local_servers import BY_ID as SERVERS
from tarjim.engines.web import reachable

START_SECONDS = 20
LOCAL_APPS = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Programs"
PLACES = {"ollama": (LOCAL_APPS / "Ollama" / "ollama.exe",),
          "lmstudio": (Path.home() / ".lmstudio" / "bin" / "lms.exe",
                       Path.home() / ".lmstudio" / "bin" / "lms"),
          "jan": (LOCAL_APPS / "Jan" / "Jan.exe", LOCAL_APPS / "jan" / "Jan.exe")}
COMMANDS = {"ollama": "ollama", "lmstudio": "lms"}
STARTS = {"ollama": ("serve",), "lmstudio": ("server", "start")}
FILES = {"ollama": ("ollama.exe", "ollama"), "lmstudio": ("lms.exe", "lms"), "jan": ("jan.exe",),
         "llamacpp": ("llama-server.exe", "llama-server"), "koboldcpp": ("koboldcpp.exe",)}
SEARCH_DEPTH = 4
SEARCH_SECONDS = 20


@dataclass
class Installed:
    id: str
    name: str
    program: str
    models: list[str] = field(default_factory=list)

    @property
    def can_start(self) -> bool:
        return self.id in STARTS


def program_of(server: str) -> str:
    from tarjim.config import setting

    remembered = setting(f"local_program_{server}")
    if remembered and Path(remembered).is_file():
        return remembered
    on_path = shutil.which(COMMANDS[server]) if server in COMMANDS else None
    return on_path or next((str(p) for p in PLACES.get(server, ()) if p.exists()), "")


def server_for(path: Path) -> str:
    return next((server for server, names in FILES.items() if path.name.lower() in names), "")


def remember(path_text: str) -> str:
    from tarjim.config import save

    path = Path(path_text.strip().strip('"'))
    server = server_for(path) if path.is_file() else ""
    if server:
        save(f"local_program_{server}", str(path))
    return server


def roots() -> list[Path]:
    names = ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA", "APPDATA")
    found = [Path(os.environ[name]) for name in names if os.environ.get(name)]
    return [*found, Path.home()]


def walk(folder: Path, depth: int, deadline: float, found: dict[str, str]) -> None:
    if depth < 0 or time.monotonic() > deadline:
        return
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return
    for entry in entries:
        if entry.is_file(follow_symlinks=False) and server_for(Path(entry.name)):
            found.setdefault(server_for(Path(entry.name)), entry.path)
        elif entry.is_dir(follow_symlinks=False) and not entry.name.startswith((".git", "$")):
            walk(Path(entry.path), depth - 1, deadline, found)


def search() -> list[str]:
    """Look through the program folders and the home folder, after the person allowed it."""
    found: dict[str, str] = {}
    deadline = time.monotonic() + SEARCH_SECONDS
    for root in roots():
        walk(root, SEARCH_DEPTH, deadline, found)
    return sorted(server for server, path in found.items() if remember(path))


def ollama_models() -> list[str]:
    folder = Path(os.environ.get("OLLAMA_MODELS", Path.home() / ".ollama" / "models"))
    library = folder / "manifests" / "registry.ollama.ai" / "library"
    if not library.is_dir():
        return []
    return sorted(f"{name.name}:{tag.name}" for name in library.iterdir() if name.is_dir()
                  for tag in name.iterdir() if tag.is_file())


def installed(running: set[str]) -> list[Installed]:
    found = []
    for server in FILES:
        program = program_of(server)
        if program and server not in running:
            models = ollama_models() if server == "ollama" else []
            found.append(Installed(server, SERVERS[server][0], program, models))
    return found


def start(server: str) -> bool:
    program = program_of(server) if server in STARTS else ""
    if not program:
        return False
    from tarjim.installer import HOME, start_detached

    HOME.mkdir(parents=True, exist_ok=True)
    start_detached([program, *STARTS[server]], HOME / f"{server}.log")
    address = SERVERS[server][1]
    probe = f"{address}/api/tags" if server == "ollama" else f"{address}/v1/models"
    deadline = time.monotonic() + START_SECONDS
    while time.monotonic() < deadline:
        if reachable(probe, {}):
            return True
        time.sleep(1)
    return False
