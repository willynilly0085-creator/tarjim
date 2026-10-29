"""Find AI programs already running on this computer and the models each one has."""
import json
import socket
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from tarjim.config import setting
from tarjim.engines.compatible import CompatibleAsker, list_models
from tarjim.engines.web import LOCAL_CUES, local_seconds

KNOWN = (("ollama", "Ollama", "http://127.0.0.1:11434"),
         ("lmstudio", "LM Studio", "http://127.0.0.1:1234"),
         ("jan", "Jan", "http://127.0.0.1:1337"),
         ("llamacpp", "llama.cpp", "http://127.0.0.1:8080"),
         ("vllm", "vLLM", "http://127.0.0.1:8000"),
         ("koboldcpp", "KoboldCpp", "http://127.0.0.1:5001"))
BY_ID = {server: (name, url) for server, name, url in KNOWN}
OLLAMA = "ollama"
QUICK = 0.3


@dataclass
class LocalServer:
    id: str
    name: str
    url: str
    models: list[str] = field(default_factory=list)


def models_of(server: str, url: str) -> list[str]:
    if server == OLLAMA:
        from tarjim.engines.ollama import installed_models

        return installed_models()
    return list_models(f"{url}/v1")


def answering(url: str) -> bool:
    """Whether anything listens there. A program on this computer accepts in milliseconds; on
    Windows a closed port is only refused after two seconds, so waiting longer tells nothing."""
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    try:
        socket.create_connection((parts.hostname or "", parts.port or 80), QUICK).close()
    except OSError:
        return False
    return True


def alive(server: str, url: str) -> bool:
    from tarjim.engines.web import reachable

    path = f"{url}/api/tags" if server == OLLAMA else f"{url}/v1/models"
    return answering(url) and reachable(path, {})


def discover() -> list[LocalServer]:
    """Every AI program answering on this computer, even one that has no model yet."""
    def probe(row: tuple[str, str, str]) -> LocalServer | None:
        server, name, url = row
        if not alive(server, url):
            return None
        return LocalServer(server, name, url, models_of(server, url))

    with ThreadPoolExecutor(max_workers=len(KNOWN)) as pool:
        return [found for found in pool.map(probe, KNOWN) if found]


class LocalAsker(CompatibleAsker):
    """A program on this computer, maybe on the processor alone: small batches, more time."""

    most_cues = LOCAL_CUES

    def seconds(self, body: dict[str, Any]) -> float:
        return local_seconds(json.dumps(body["messages"], ensure_ascii=False))


def chosen_server() -> str:
    picked = setting("local_server")
    return picked if picked in BY_ID else OLLAMA


def local_asker() -> LocalAsker | None:
    server = chosen_server()
    if server == OLLAMA:
        return None
    _name, url = BY_ID[server]
    return LocalAsker(server, f"{url}/v1", "", setting("local_model"))
