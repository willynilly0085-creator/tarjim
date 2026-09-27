import re
from pathlib import Path
from typing import Any, ClassVar

from tarjim.config import save, setting
from tarjim.engines.choice import LISTENERS, TRANSLATORS, chosen
from tarjim.engines.subscription import installed
from tarjim.keys import status
from tarjim.server.guard import extension_origin
from tarjim.server.pairing import Pairing
from tarjim.tools import Shelf

UI_LANGUAGES = ("ar", "en")
MODEL_TAG = re.compile(r"^[\w.:/-]{2,80}$")
EXTENSION = Path(__file__).resolve().parents[2] / "extension"
FIELDS: dict[str, tuple[str, ...]] = {"ui_language": UI_LANGUAGES, "listen_provider": LISTENERS,
                                      "translate_provider": TRANSLATORS, "setup_done": ("yes",)}
Query = dict[str, list[str]]


class SetupRoutes:
    shelf: ClassVar[Shelf]
    pairing: ClassVar[Pairing]
    token: ClassVar[str]
    headers: Any

    def reply(self, code: int, payload: Any) -> None:
        raise NotImplementedError

    def read_json(self) -> dict[str, Any]:
        raise NotImplementedError

    def ui_language(self, _query: Query) -> None:
        self.reply(200, {"language": setting("ui_language")})

    def local_models(self, _query: Query) -> None:
        from tarjim.engines.ollama import installed_models

        self.reply(200, {"models": installed_models(), "chosen": setting("local_model")})

    def system(self, _query: Query) -> None:
        from tarjim.system import describe

        self.reply(200, describe())

    def setup_state(self, _query: Query) -> None:
        state: dict[str, Any] = {name: setting(name) for name in FIELDS}
        state["keys"] = status()
        state["chosen"] = {"listen": chosen("listen"), "translate": chosen("translate")}
        folder = EXTENSION if EXTENSION.is_dir() else None
        state["extension_path"] = str(folder) if folder else ""
        state["local_model"] = setting("local_model")
        state["subscriptions"] = installed()
        self.reply(200, state)

    def save_setup(self, query: Query) -> None:
        data = self.read_json()
        for name, allowed in FIELDS.items():
            if data.get(name) in allowed:
                save(name, str(data[name]))
        if MODEL_TAG.match(str(data.get("local_model", ""))):
            save("local_model", str(data["local_model"]))
        self.setup_state(query)

    def list_tools(self, _query: Query) -> None:
        self.reply(200, self.shelf.view())

    def get_tool(self, _query: Query, tool_id: str) -> None:
        started = self.shelf.start(tool_id)
        self.reply(200 if started else 409, {"started": started})

    def ask_pair(self, _query: Query) -> None:
        origin = self.headers.get("Origin", "")
        request = self.pairing.ask(origin) if extension_origin(origin) else None
        if request is None:
            self.reply(403, {"error": "pair"})
            return
        self.reply(200, {"id": request.id})

    def pair_state(self, _query: Query, request_id: str) -> None:
        self.reply(200, self.pairing.claim(request_id, self.token))

    def list_pairs(self, _query: Query) -> None:
        self.reply(200, [{"id": r.id, "origin": r.origin} for r in self.pairing.pending()])

    def decide_pair(self, _query: Query, request_id: str, verdict: str) -> None:
        done = self.pairing.decide(request_id, verdict == "allow")
        self.reply(200 if done else 404, {"done": done})
