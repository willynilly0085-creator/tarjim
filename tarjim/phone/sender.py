"""Send the finished result to the phone and show each step in the job's own message: preparing a
phone copy, sending it (with its size), sent. A failed upload is retried, and if it still fails the
person is told, gets the subtitle file, and the full video stays on the computer."""
import time
from pathlib import Path
from typing import Any

from tarjim.phone.delivery import chosen_output, phone_copy
from tarjim.phone.telegram import Bot, TelegramError
from tarjim.phone.words import result_name, say

ATTEMPTS = 3
PAUSE = 10.0
MB = 1024 * 1024


class Sender:
    def __init__(self, bot: Bot, chat: int, message: int, task: Any) -> None:
        self.bot, self.chat, self.message, self.task = bot, chat, message, task
        view = task.view()
        self.head = f"{view['title']}\n{result_name(str(view['mode']))}"

    def tell(self, key: str) -> None:
        """A failure is also sent as a new message, so the phone notifies the person."""
        self.show(key)
        try:
            self.bot.say(self.chat, say(key))
        except TelegramError:
            return

    def show(self, key: str, **values: object) -> None:
        try:
            self.bot.edit(self.chat, self.message, f"{self.head} · {say(key, **values)}")
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
            self.tell(f"err_{self.task.error_code or 'unknown'}")
        elif self.task.stage == "done":
            self.send(list(self.task.outputs), str(self.task.order.mode))

    def send(self, outputs: list[Path], mode: str) -> None:
        wanted = chosen_output(outputs, mode)
        if wanted is None:
            self.tell("err_unknown")
            return
        if wanted.suffix == ".mp4":
            self.show("phone_preparing")
        ready = phone_copy(wanted) if wanted.suffix == ".mp4" else wanted
        if ready is not None:
            self.show("phone_sending", mb=max(1, round(ready.stat().st_size / MB)))
            sent = self.upload(ready)
            if ready != wanted:
                ready.unlink(missing_ok=True)
            if sent:
                self.show("phone_sent")
                return
        self.fall_back(outputs, "phone_too_big" if ready is None else "phone_send_failed")

    def fall_back(self, outputs: list[Path], reason: str) -> None:
        subtitles = chosen_output(outputs, "srt")
        if subtitles is not None:
            self.upload(subtitles)
        self.tell(reason)
