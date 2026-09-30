"""Keep one message per job up to date with its stage, and send the result when it is ready."""
import json
import threading
from dataclasses import dataclass
from typing import Any, Protocol

from tarjim.phone.sender import Sender
from tarjim.phone.telegram import Bot, TelegramError
from tarjim.phone.words import result_name, say

TICK = 3.0


class Jobs(Protocol):
    def submit(self, order: Any) -> Any: ...
    def get(self, task_id: str) -> Any: ...
    def steer(self, task_id: str, action: str, source: str = "") -> Any: ...


@dataclass
class Watch:
    chat: int
    message: int
    shown: str = ""


def cancel_button(task_id: str) -> str:
    return json.dumps({"inline_keyboard": [[{"text": say("cancel"),
                                             "callback_data": f"cancel:{task_id}"}]]})


def status_text(task: Any) -> str:
    view = task.view()
    stage = "paused" if view["paused"] else view["stage"]
    return f"{view['title']}\n{result_name(str(view['mode']))} · {say(f'stage_{stage}')}"


class Follower:
    def __init__(self, jobs: Jobs) -> None:
        self.jobs = jobs
        self.watching: dict[str, Watch] = {}
        self.lock = threading.Lock()

    def adopt(self, bot: Bot, chat: int, message: int, task: Any) -> None:
        """Turn the question message into this job's status message."""
        text = status_text(task)
        bot.edit(chat, message, text, reply_markup=cancel_button(task.id))
        with self.lock:
            self.watching[task.id] = Watch(chat, message, text)

    def run(self, bot_now: Any, stop: threading.Event) -> None:
        while not stop.wait(TICK):
            bot = bot_now()
            if bot is not None:
                self.tick(bot)

    def tick(self, bot: Bot) -> None:
        with self.lock:
            watched = list(self.watching.items())
        for task_id, watch in watched:
            task = self.jobs.get(task_id)
            if task is None:
                self.forget(task_id)
                continue
            self.refresh(bot, task, watch)
            if task.finished:
                self.forget(task_id)
                threading.Thread(target=deliver, args=(bot, watch, task), daemon=True).start()

    def refresh(self, bot: Bot, task: Any, watch: Watch) -> None:
        text = status_text(task)
        if text == watch.shown:
            return
        extra = {} if task.finished else {"reply_markup": cancel_button(task.id)}
        try:
            bot.edit(watch.chat, watch.message, text, **extra)
            watch.shown = text
        except TelegramError:
            return

    def forget(self, task_id: str) -> None:
        with self.lock:
            self.watching.pop(task_id, None)


def deliver(bot: Bot, watch: Watch, task: Any) -> None:
    Sender(bot, watch.chat, watch.message, task).deliver()
