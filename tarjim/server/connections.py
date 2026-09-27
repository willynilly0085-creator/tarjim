"""The connections screen: API keys, subscriptions and AI on this computer, in one view."""
import re
import subprocess
import sys
from typing import Any

from tarjim.config import save, setting
from tarjim.engines.catalog import API, BY_ID, LOCAL, SUBSCRIPTION, Provider, compatible, of_method
from tarjim.engines.choice import LISTENERS, chosen, has_key

MODEL_NAME = re.compile(r"^[\w.:/@+-]{1,120}$")
ADDRESS = re.compile(r"^https?://[\w.-]+(:\d{1,5})?(/[\w./-]*)?$")
Query = dict[str, list[str]]


def api_view(provider: Provider) -> dict[str, Any]:
    view = {"id": provider.id, "name": provider.name, "hears": provider.hears,
            "key_url": provider.key_url, "has_key": bool(setting(provider.key_name)),
            "ready": has_key(provider.id), "model": setting(provider.model_name)}
    return {**view, "base_url": setting("custom_base_url")} if provider.id == "custom" else view


def subscription_view(provider: Provider) -> dict[str, Any]:
    from tarjim.engines.subscription import codex_models, launcher

    models = codex_models() if provider.id == "codex" else list(provider.models)
    return {"id": provider.id, "name": provider.name, "ready": bool(launcher(provider.program)),
            "install": provider.install, "model": setting(provider.model_name),
            "models": [m for m in models if m]}


def local_view() -> dict[str, Any]:
    from tarjim.engines.local_servers import chosen_server, discover

    servers = [{"id": s.id, "name": s.name, "url": s.url, "models": s.models} for s in discover()]
    return {"servers": servers, "server": chosen_server(), "model": setting("local_model")}


def overview() -> dict[str, Any]:
    return {"api": [api_view(p) for p in of_method(API)],
            "subscription": [subscription_view(p) for p in of_method(SUBSCRIPTION)],
            "local": local_view(),
            "chosen": {"listen": chosen("listen"), "translate": chosen("translate")}}


def method_of(provider: str) -> str:
    return BY_ID[provider].method if provider in BY_ID else LOCAL


def listener_for(provider: str) -> str:
    if provider in LISTENERS and provider != LOCAL and has_key(provider):
        return provider
    return "gemini" if has_key("gemini") else LOCAL


def remember_choice(data: dict[str, Any]) -> bool:
    provider, model = str(data.get("provider", "")), str(data.get("model", ""))
    if provider != LOCAL and provider not in BY_ID:
        return False
    if model and not MODEL_NAME.match(model):
        return False
    if provider == LOCAL:
        from tarjim.engines.local_servers import BY_ID as SERVERS

        server = str(data.get("server", "ollama"))
        if server not in SERVERS:
            return False
        save("local_server", server)
    if model:
        save("local_model" if provider == LOCAL else BY_ID[provider].model_name, model)
    save("translate_provider", provider)
    save("listen_provider", str(data.get("listen") or listener_for(provider)))
    return True


def models_for(provider: str) -> list[str]:
    from tarjim.engines.compatible import address, list_models

    found = BY_ID.get(provider)
    if found is None or not compatible(found) or not setting(found.key_name):
        return []
    return list_models(address(provider), setting(found.key_name))


def open_console(command: list[str]) -> bool:
    if sys.platform != "win32" or not command:
        return False
    subprocess.Popen(["cmd", "/c", "start", "tarjim", "cmd", "/k", *command])
    return True


class ConnectionRoutes:
    def reply(self, code: int, payload: Any) -> None:
        raise NotImplementedError

    def read_json(self) -> dict[str, Any]:
        raise NotImplementedError

    def connections(self, _query: Query) -> None:
        self.reply(200, overview())

    def connection_models(self, _query: Query) -> None:
        self.reply(200, {"models": models_for(str(self.read_json().get("provider", "")))})

    def use_connection(self, _query: Query) -> None:
        saved = remember_choice(self.read_json())
        self.reply(200 if saved else 400, overview())

    def save_address(self, _query: Query) -> None:
        url = str(self.read_json().get("url", "")).rstrip("/")
        if not ADDRESS.match(url):
            self.reply(400, {"error": "address"})
            return
        save("custom_base_url", url)
        self.reply(200, {"saved": True})

    def sign_in(self, _query: Query) -> None:
        from tarjim.engines.subscription import launcher

        found = BY_ID.get(str(self.read_json().get("provider", "")))
        if found is None or found.method != SUBSCRIPTION:
            self.reply(400, {"error": "provider"})
            return
        command = [*launcher(found.program), *found.login[1:]]
        self.reply(200, {"opened": open_console(command)})

    def link_assistant(self, _query: Query) -> None:
        from tarjim.server.assistant_link import link

        app = str(self.read_json().get("app", ""))
        done, detail = link(app)
        self.reply(200 if done else 400, {"linked": done, "detail": detail})
