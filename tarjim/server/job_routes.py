"""What the page does to a job: check an order before sending it, open its file or folder, pause,
cancel, retry, remove. Each one answers with a reason the page can show under the job."""
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from tarjim import x_posts
from tarjim.server import desktop
from tarjim.server.jobs import DUBBING, MODES, Board, Order
from tarjim.server.orders import order_from

Query = dict[str, list[str]]
X_REFUSED = ("x_signin", "x_account")


def refusal(order: Order) -> str:
    """Why an order cannot be made, found when it is sent and not at the end of the work."""
    from tarjim.translate.prompt import DIALECTS

    if order.mode not in MODES:
        return "mode"
    if order.dialect not in DIALECTS:  # the prompt looked it up mid-job (2026-11-09)
        return "dialect"
    if order.tweaks and tweak_reasons(order):
        return "tweaks"
    if order.mode not in DUBBING:
        return ""
    from tarjim.dub.make import DubUnavailable, choose

    try:
        choose(DUBBING[order.mode], order.target)
    except DubUnavailable as error:
        return "dub_key" if "API key" in str(error) else "dub_language"
    return ""


def tweak_reasons(order: Order) -> dict[str, str]:
    """Why each of the order's own changes cannot be made: not a setting, not for one video,
    a font this computer cannot write the language in, or a broken rule. Refused before the
    job starts (2026-11-09)."""
    from tarjim.prefs.job import vetted
    from tarjim.prefs.store import load
    from tarjim.prefs.view import font_refused

    found = vetted(load().values, order.tweaks, order.target)
    return {**font_refused(order.tweaks, order.target),
            **{key: refusal.reason for key, refusal in found.items()}}


def refused(order: Order, reason: str) -> dict[str, Any]:
    """The answer to an order that cannot be made; with each refused change's reason."""
    return {"error": reason, "refused": tweak_reasons(order)} if reason == "tweaks" else {
        "error": reason}


class JobRoutes:
    board: ClassVar[Board]

    def reply(self, code: int, payload: Any) -> None:
        raise NotImplementedError

    def read_json(self) -> dict[str, Any]:
        raise NotImplementedError

    def check_order(self, _query: Query) -> None:
        order = order_from("", self.read_json())
        reason = refusal(order)
        self.reply(400, refused(order, reason)) if reason else self.reply(200, {"ok": True})

    def reveal(self, _query: Query, task_id: str) -> None:
        self.on_output(task_id, desktop.reveal)

    def play(self, _query: Query, task_id: str) -> None:
        self.on_output(task_id, desktop.open_file)

    def on_output(self, task_id: str, action: Callable[[Path], None]) -> None:
        task = self.board.get(task_id)
        if not task or not task.outputs:
            return self.reply(404, {"error": "job"})
        if not task.outputs[0].exists():  # moved or deleted since the job ended
            return self.reply(404, {"error": "gone"})
        try:
            action(task.outputs[0])
        except OSError:
            return self.reply(500, {"error": "open"})
        self.reply(200, {"ok": True})

    def steer_job(self, _query: Query, task_id: str, action: str) -> None:
        task = self.board.steer(task_id, action, getattr(self, "headers", {}).get("Origin")
                                or "chat or script")
        self.reply(200, task.view()) if task else self.reply(409, {"error": "job"})

    def remove_job(self, _query: Query, task_id: str) -> None:
        removed = self.board.remove(task_id)  # the list only: its files stay in their folder
        self.reply(200 if removed else 409, {"removed": removed})

    def retry(self, _query: Query, task_id: str) -> None:
        task = self.board.retry(task_id)
        self.reply(200, task.view()) if task else self.reply(404, {"error": "job"})

    def retry_signed_in(self, _query: Query, task_id: str) -> None:
        """Again, with the person's own X sign-in for this one download (x_posts.py). Only a
        job X refused, and only X's cookies: none is kept when none of them signs anyone in."""
        task = self.board.get(task_id)
        source = task.order.source if task else ""
        if not task or task.error_code not in X_REFUSED or not x_posts.is_x(source):
            return self.reply(409, {"error": "job"})
        if not x_posts.hold(source, self.read_json().get("cookies")):
            return self.reply(422, {"error": "x_none"})
        again = self.board.retry(task_id)
        if again is None:
            x_posts.take(source)  # not used: forgotten now
            return self.reply(409, {"error": "job"})
        self.reply(200, again.view())

    def relisten(self, _query: Query, task_id: str) -> None:
        task = self.board.relisten(task_id)
        self.reply(200, task.view()) if task else self.reply(404, {"error": "job"})
