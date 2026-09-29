"""The connections screen: API keys, subscriptions and AI on this computer, in one view."""
import re
from typing import Any

from tarjim.config import save, setting
from tarjim.engines.catalog import API, BY_ID, LOCAL, SUBSCRIPTION, Provider, compatible, of_method
from tarjim.engines.choice import LISTENERS, chosen, has_key

MODEL_NAME = re.compile(r"^[\w.:/@+\[\]-]{1,120}$")
ADDRESS = re.compile(r"^https?://[\w.-]+(:\d{1,5})?(/[\w./-]*)?$")
Query = dict[str, list[str]]


def api_view(provider: Provider) -> dict[str, Any]:
    view = {"id": provider.id, "name": provider.name, "hears": provider.hears,
            "key_url": provider.key_url, "has_key": bool(setting(provider.key_name)),
            "ready": has_key(provider.id), "model": setting(provider.model_name)}
    return {**view, "base_url": setting("custom_base_url")} if provider.id == "custom" else view


def subscription_view(provider: Provider) -> dict[str, Any]:
    from tarjim.engines import app_install
    from tarjim.engines.subscription import codex_models, launcher

    labels: dict[str, str] = {}
    if provider.id == "claude":
        from tarjim.engines.subscription_models import claude_models

        labels = dict(claude_models())
    models = codex_models() if provider.id == "codex" else list(labels or provider.models)
    return {"id": provider.id, "name": provider.name, "ready": bool(launcher(provider.program)),
            "model_labels": {m: text for m, text in labels.items() if text},
            "install": provider.install, "model": setting(provider.model_name),
            "models": [m for m in models if m], "node": bool(app_install.npm()),
            "can_install": provider.id in app_install.PACKAGES and bool(
                app_install.npm() or provider.id in app_install.NATIVE),
            "installing": app_install.installing(provider.id),
            "install_failed": app_install.failed(provider.id)}


def local_view() -> dict[str, Any]:
    from tarjim.engines.local_programs import installed
    from tarjim.engines.local_servers import chosen_server, discover

    running = discover()
    servers = [{"id": s.id, "name": s.name, "url": s.url, "models": s.models} for s in running]
    stopped = [{"id": p.id, "name": p.name, "models": p.models, "can_start": p.can_start}
               for p in installed({s.id for s in running})]
    return {"servers": servers, "installed": stopped, "server": chosen_server(),
            "model": setting("local_model")}


def overview() -> dict[str, Any]:
    from tarjim.engines.listening import listening_overview

    return {"api": [api_view(p) for p in of_method(API)], "listening": listening_overview(),
            "subscription": [subscription_view(p) for p in of_method(SUBSCRIPTION)],
            "local": local_view(),
            "chosen": {"listen": chosen("listen"), "translate": chosen("translate")}}


def method_of(provider: str) -> str:
    return BY_ID[provider].method if provider in BY_ID else LOCAL


def listener_for(provider: str) -> str:
    if provider in LISTENERS and provider != LOCAL and has_key(provider):
        return provider
    return "gemini" if has_key("gemini") else LOCAL


def acceptable(provider: str, listen: str, model: str) -> bool:
    known = provider == LOCAL or provider in BY_ID
    hears = listen in LISTENERS and (listen == LOCAL or has_key(listen))
    return known and hears and (not model or bool(MODEL_NAME.match(model)))


def remember_choice(data: dict[str, Any]) -> bool:
    provider, model = str(data.get("provider", "")), str(data.get("model", ""))
    listen = str(data.get("listen") or listener_for(provider))
    if not acceptable(provider, listen, model):
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
    save("listen_provider", listen)
    return True


def models_for(provider: str) -> list[str]:
    from tarjim.engines.compatible import address, list_models

    found = BY_ID.get(provider)
    if found is None or not compatible(found) or not setting(found.key_name):
        return []
    return list_models(address(provider), setting(found.key_name))


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
        from tarjim.engines.sign_in import start

        mode = start(str(self.read_json().get("provider", "")))
        self.reply(200 if mode else 400, {"mode": mode})

    def sign_in_code(self, _query: Query) -> None:
        from tarjim.engines.sign_in import send_code

        data = self.read_json()
        sent = send_code(str(data.get("provider", "")), str(data.get("code", "")).strip())
        self.reply(200 if sent else 400, {"sent": sent})

    def start_local(self, _query: Query) -> None:
        from tarjim.engines.local_programs import start

        started = start(str(self.read_json().get("server", "")))
        self.reply(200 if started else 400, {"started": started, **overview()})

    def install_app(self, _query: Query) -> None:
        from tarjim.engines.app_install import start

        result = start(str(self.read_json().get("provider", "")))
        self.reply(200 if result == "started" else 400, {"result": result, **overview()})

    def scan_local(self, _query: Query) -> None:
        from tarjim.engines.local_programs import search

        self.reply(200, {"found": search(), **overview()})

    def local_program(self, _query: Query) -> None:
        from tarjim.engines.local_programs import remember

        server = remember(str(self.read_json().get("path", "")))
        self.reply(200 if server else 400, {"server": server, **overview()})

    def signed_in(self, _query: Query) -> None:
        from tarjim.engines.sign_in import signed_in

        provider = str(self.read_json().get("provider", ""))
        self.reply(200, {"signed_in": provider in BY_ID and signed_in(provider)})

    def link_assistant(self, _query: Query) -> None:
        from tarjim.server.assistant_link import link

        app = str(self.read_json().get("app", ""))
        done, detail = link(app)
        self.reply(200 if done else 400, {"linked": done, "detail": detail})
