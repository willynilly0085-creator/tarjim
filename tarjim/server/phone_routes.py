"""Settings for the phone: connect a Telegram bot, pair a phone with it, choose what it returns."""
from typing import Any

from tarjim.config import save
from tarjim.languages import LANGUAGES
from tarjim.phone import large
from tarjim.phone.choice import MODES
from tarjim.phone.service import service
from tarjim.translate.prompt import DIALECTS

Query = dict[str, list[str]]
CHOICES = {"phone_target": tuple(LANGUAGES), "phone_mode": MODES,
           "phone_dialect": tuple(DIALECTS)}


class PhoneRoutes:
    def reply(self, code: int, payload: Any) -> None:
        raise NotImplementedError

    def read_json(self) -> dict[str, Any]:
        raise NotImplementedError

    def phone_state(self, _query: Query) -> None:
        self.reply(200, service.view())

    def phone_connect(self, _query: Query) -> None:
        result = service.connect(str(self.read_json().get("token", "")).strip())
        self.reply(400 if "error" in result else 200, result)

    def phone_link(self, _query: Query) -> None:
        self.reply(200, service.view(link=True))

    def phone_forget(self, _query: Query) -> None:
        self.reply(200, service.forget())

    def phone_large(self, _query: Query) -> None:
        """Turn large videos on with Telegram's app id and hash, after Telegram accepts them;
        empty fields turn it off."""
        data = self.read_json()
        app_id, app_hash = (str(data.get(name, "")).strip() for name in ("api_id", "api_hash"))
        large.forget()
        if not app_id and not app_hash:
            return self.reply(200, service.view())
        if not large.well_formed(app_id, app_hash):
            return self.reply(400, {"error": "large", **service.view()})
        save("telegram_api_id", app_id)
        save("telegram_api_hash", app_hash)
        if not large.works():
            large.forget()
            return self.reply(400, {"error": "large", **service.view()})
        self.reply(200, service.view())

    def phone_choices(self, _query: Query) -> None:
        data = self.read_json()
        for name, allowed in CHOICES.items():
            if data.get(name.removeprefix("phone_")) in allowed:
                save(name, str(data[name.removeprefix("phone_")]))
        self.reply(200, service.view())
