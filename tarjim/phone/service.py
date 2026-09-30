"""Run the phone bot next to the engine: connect a bot, show the pairing code, keep polling."""
import json
import threading
from pathlib import Path
from typing import Any

from tarjim.config import save, setting
from tarjim.phone.bot import Inbox, Pairing
from tarjim.phone.progress import Follower, Jobs
from tarjim.phone.telegram import Bot, TelegramError, well_formed
from tarjim.phone.words import say

RETRY = (5, 15, 30, 60)
COMMANDS = ("mode", "help")


class Service:
    def __init__(self) -> None:
        self.pairing = Pairing()
        self.stop = threading.Event()
        self.problem = ""
        self.inbox: Inbox | None = None
        self.threads: list[threading.Thread] = []

    def bot(self) -> Bot | None:
        token = setting("telegram_token")
        return Bot(token) if token and self.problem != "rejected" else None

    def begin(self, jobs: Jobs, uploads: Path) -> None:
        if any(thread.is_alive() for thread in self.threads):
            return
        follower = Follower(jobs)
        self.inbox = Inbox(follower, uploads, self.pairing)
        self.stop.clear()
        self.threads = [threading.Thread(target=self.poll, daemon=True),
                        threading.Thread(target=follower.run, args=(self.bot, self.stop),
                                         daemon=True)]
        for thread in self.threads:
            thread.start()

    def poll(self) -> None:
        misses = 0
        while not self.stop.is_set():
            bot = self.bot()
            if bot is None or self.inbox is None:
                self.stop.wait(RETRY[-1])
                continue
            try:
                self.receive(bot)
                self.problem, misses = "", 0
            except TelegramError as error:
                self.problem = {401: "rejected", 409: "elsewhere"}.get(error.code, "offline")
                self.stop.wait(RETRY[min(misses, len(RETRY) - 1)])
                misses += 1

    def receive(self, bot: Bot) -> None:
        for update in bot.updates(int(setting("phone_offset") or 0)):
            save("phone_offset", str(int(update["update_id"]) + 1))
            try:
                if self.inbox is not None:
                    self.inbox.handle(bot, update)
            except (TelegramError, OSError, KeyError, ValueError):
                continue

    def connect(self, token: str) -> dict[str, Any]:
        if not well_formed(token):
            return {"error": "token"}
        bot = Bot(token)
        try:
            name = str(bot.me()["username"])
            bot.call("deleteWebhook")
            bot.call("setMyCommands", commands=json.dumps(
                [{"command": c, "description": say(f"phone_cmd_{c}")} for c in COMMANDS]))
        except TelegramError as error:
            return {"error": "rejected" if error.code in (401, 404) else "offline"}
        if name != setting("phone_bot"):
            save("phone_chat", "")
            save("phone_offset", "0")
        save("telegram_token", token)
        save("phone_bot", name)
        self.problem = ""
        return self.view(link=True)

    def forget(self) -> dict[str, Any]:
        for name in ("telegram_token", "phone_bot", "phone_chat", "phone_offset"):
            save(name, "")
        self.pairing = Pairing()
        if self.inbox is not None:
            self.inbox.pairing = self.pairing
        return self.view()

    def view(self, link: bool = False) -> dict[str, Any]:
        name = setting("phone_bot") if setting("telegram_token") else ""
        paired = bool(name and setting("phone_chat"))
        view: dict[str, Any] = {"bot": name, "paired": paired, "problem": self.problem,
                                "target": setting("phone_target") or "ar",
                                "mode": setting("phone_mode") or "burn",
                                "dialect": setting("phone_dialect") or "saudi"}
        if name and not paired and link:
            address = f"https://t.me/{name}?start={self.pairing.fresh()}"
            view.update(link=address, qr=qr_image(address))
        return view


def qr_image(text: str) -> str:
    import segno

    return str(segno.make(text, error="m").svg_data_uri(scale=6, border=2, dark="#1a1814",
                                                        light="#f7f5ef"))


service = Service()
