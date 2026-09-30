import re
from typing import Any, ClassVar

from tarjim import autostart
from tarjim.config import save, setting
from tarjim.engines.choice import LISTENERS, TRANSLATORS, chosen
from tarjim.engines.subscription import installed
from tarjim.extension_home import extension_folder
from tarjim.keys import status
from tarjim.server.guard import extension_origin
from tarjim.server.onboard_routes import OnboardRoutes
from tarjim.server.pairing import Pairing
from tarjim.tools import Shelf
from tarjim.ui_languages import available, codes

GLOSSARY_CHARS = 5000
MODEL_TAG = re.compile(r"^[\w.:/-]{2,80}$")
FIELDS: dict[str, tuple[str, ...]] = {"ui_language": codes(), "listen_provider": LISTENERS,
                                      "translate_provider": TRANSLATORS, "setup_done": ("yes",)}
Query = dict[str, list[str]]


def setup_finished() -> bool:
    """Someone who set tarjim up before the setup assistant existed has already picked a translator,
    so an update does not send them through setup again."""
    return setting("setup_done") == "yes" or setting("translate_provider") in TRANSLATORS


class SetupRoutes(OnboardRoutes):
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
        from tarjim.engines.local_servers import BY_ID, chosen_server, models_of

        server = chosen_server()
        models = models_of(server, BY_ID[server][1])
        self.reply(200, {"models": models, "chosen": setting("local_model"), "server": server})

    def system(self, _query: Query) -> None:
        from tarjim.system import describe

        self.reply(200, describe())

    def setup_state(self, _query: Query) -> None:
        state: dict[str, Any] = {name: setting(name) for name in FIELDS}
        state["keys"] = status()
        state["chosen"] = {"listen": chosen("listen"), "translate": chosen("translate")}
        state["setup_done"] = "yes" if setup_finished() else ""
        state["extension_path"] = extension_folder()
        state["local_model"] = setting("local_model")
        state["glossary"] = setting("glossary")
        state["subscriptions"] = installed()
        state["ui_languages"] = list(available())
        state["autostart"] = autostart.enabled()
        self.reply(200, state)

    def save_setup(self, query: Query) -> None:
        data = self.read_json()
        for name, allowed in FIELDS.items():
            if data.get(name) in allowed:
                save(name, str(data[name]))
        if isinstance(data.get("glossary"), str) and len(data["glossary"]) <= GLOSSARY_CHARS:
            save("glossary", data["glossary"])
        if isinstance(data.get("autostart"), bool):
            (autostart.enable if data["autostart"] else autostart.disable)()
        if MODEL_TAG.match(str(data.get("local_model", ""))):
            save("local_model", str(data["local_model"]))
        self.setup_state(query)

    def list_tools(self, _query: Query) -> None:
        self.reply(200, self.shelf.view())

    def get_tool(self, _query: Query, tool_id: str) -> None:
        accepted = self.read_json().get("accept_license") is True
        result = self.shelf.start(tool_id, accepted)
        self.reply(200 if result == "started" else 409, {"started": result == "started",
                                                         "result": result})

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
