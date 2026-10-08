"""Send the finished result to the phone and show each step in the job's checklist: preparing a
phone copy, sending it (with its size), sent. A failed upload is retried; if it still fails, the
person is told in a new message and gets the subtitle file, and the video stays on the computer."""
import time
from pathlib import Path
from typing import Any

from tarjim.phone.checklist import checklist
from tarjim.phone.delivery import chosen_output, phone_copy
from tarjim.phone.telegram import Bot, TelegramError
from tarjim.phone.words import say

ATTEMPTS = 3
PAUSE = 10.0
MB = 1024 * 1024


class Sender:
    def __init__(self, bot: Bot, chat: int, message: int, task: Any) -> None:
        self.bot, self.chat, self.message, self.task = bot, chat, message, task

    def show(self, step: str, note: str = "", stopped: bool = False) -> None:
        try:
            self.bot.edit(self.chat, self.message, checklist(self.task, step, note, stopped))
        except TelegramError:
            return

    def tell(self, key: str, detail: str = "") -> None:
        """A problem is sent as a new message too, so the phone notifies the person, with the
        real reason under it."""
        text = "\n".join([say(key), say("errorDetail", detail=detail)] if detail else [say(key)])
        try:
            self.bot.say(self.chat, text)
        except TelegramError:
            return

    def upload(self, path: Path) -> bool:
        for attempt in range(ATTEMPTS):
            try:
                self.bot.send_file(self.chat, path, video=path.suffix == ".mp4")
                return True
            except TelegramError:
                if attempt < ATTEMPTS - 1:
                    time.sleep(PAUSE * (attempt + 1))
        return False

    def deliver(self) -> None:
        if self.task.stage == "failed":
            self.tell(f"err_{self.task.error_code or 'unknown'}", str(self.task.view()["detail"]))
        elif self.task.stage == "done":
            self.send(list(self.task.outputs), str(self.task.order.mode))

    def send(self, outputs: list[Path], mode: str) -> None:
        wanted = chosen_output(outputs, mode)
        if wanted is None:
            self.show("send", stopped=True)
            self.tell("err_unknown")
            return
        if wanted.suffix == ".mp4":
            self.show("prepare")
        ready = phone_copy(wanted) if wanted.suffix == ".mp4" else wanted
        if ready is not None:
            self.show("send", say("phone_size", mb=max(1, round(ready.stat().st_size / MB))))
            sent = self.upload(ready)
            if ready != wanted:
                ready.unlink(missing_ok=True)
            if sent:
                self.show("sent")
                return
        self.show("send", stopped=True)
        self.fall_back(outputs, "phone_too_big" if ready is None else "phone_send_failed")

    def fall_back(self, outputs: list[Path], reason: str) -> None:
        subtitles = chosen_output(outputs, "srt")
        if subtitles is not None:
            self.upload(subtitles)
        self.tell(reason)
