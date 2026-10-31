"""What the page does to a job: check an order before sending it, open its file or folder, pause,
cancel, retry, remove. Each one answers with a reason the page can show under the job."""
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from tarjim.server import desktop
from tarjim.server.jobs import DUBBING, MODES, Board, Order
from tarjim.server.orders import order_from

Query = dict[str, list[str]]


def refusal(order: Order) -> str:
    """Why an order cannot be made, found when it is sent and not at the end of the work."""
    if order.mode not in MODES:
        return "mode"
    if order.mode not in DUBBING:
        return ""
    from tarjim.dub.make import DubUnavailable, choose

    try:
        choose(DUBBING[order.mode], order.target)
    except DubUnavailable as error:
        return "dub_key" if "API key" in str(error) else "dub_language"
    return ""


class JobRoutes:
    board: ClassVar[Board]

    def reply(self, code: int, payload: Any) -> None:
        raise NotImplementedError

    def read_json(self) -> dict[str, Any]:
        raise NotImplementedError

    def check_order(self, _query: Query) -> None:
        refused = refusal(order_from("", self.read_json()))
        self.reply(400, {"error": refused}) if refused else self.reply(200, {"ok": True})

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

    def relisten(self, _query: Query, task_id: str) -> None:
        task = self.board.relisten(task_id)
        self.reply(200, task.view()) if task else self.reply(404, {"error": "job"})
