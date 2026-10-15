"""One job, run in a thread of its own and watched by the board.

A cancel used to take effect only at the job's next step, and some steps report nothing for
minutes (a stream the downloader hands to ffmpeg, a subscription app, a web request), so the
job went on and every later job waited. Now the board stops the programs the job started at
once, gives the thread a moment to end, takes back what the job made, marks it cancelled and
moves on. A thread still stuck (a web request in flight) is left behind: it ends by itself at
its next step, changes nothing the person sees, and takes back what it wrote late.
"""
import threading
from collections.abc import Callable

from tarjim.children import FAMILY, Family
from tarjim.job import CHECKPOINT
from tarjim.server.jobs import Stopped, Task, Worker, classify

TICK = 0.1
GRACE = 0.5
MayUndo = Callable[[Task], bool]


class Run:
    def __init__(self, task: Task, work: Worker, may_undo: MayUndo) -> None:
        self.task, self.work, self.may_undo = task, work, may_undo
        self.ok = False
        self.error: Exception | None = None
        self.ended = self.abandoned = False
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self.body, daemon=True)

    def body(self) -> None:
        FAMILY.set(self.task.family)
        CHECKPOINT.set(self.task.checkpoint)
        try:
            self.task.checkpoint()
            self.work(self.task)
            self.ok = True
        except Exception as error:
            self.error = error
        finally:
            self.close()

    def close(self) -> None:
        with self.lock:
            self.ended, late = True, self.abandoned
        if late and self.may_undo(self.task):
            self.task.take_back()

    def leave(self) -> None:
        with self.lock:
            self.abandoned = not self.ended


def pace(family: Family, paused: bool, held: bool) -> bool:
    """While paused, programs working on this computer's files are held; resumed, let go."""
    if paused:
        family.hold()
        return True
    if held:
        family.release()
    return False


def watch_over(task: Task, run: Run) -> None:
    held = False
    while run.thread.is_alive() and task.control != "cancelled":
        held = pace(task.family, task.control == "paused", held)
        run.thread.join(TICK)
    if held and task.control != "cancelled":
        task.family.release()


def cancel(task: Task, run: Run) -> None:
    task.family.stop()
    run.thread.join(GRACE)
    run.leave()
    task.take_back()
    task.stage = "cancelled"


def fail(task: Task, error: Exception) -> None:
    task.failed_at = task.stage
    task.error, task.error_code = str(error)[:300], classify(error)
    task.stage = "failed"


def carry(task: Task, work: Worker, may_undo: MayUndo) -> None:
    if task.control == "cancelled":  # cancelled while it waited its turn
        task.stage = "cancelled"
        return
    run = Run(task, work, may_undo)
    run.thread.start()
    watch_over(task, run)
    if (task.control == "cancelled" and not run.ok) or isinstance(run.error, Stopped):
        cancel(task, run)
    elif run.ok:
        task.stage = "done"
    else:
        fail(task, run.error or RuntimeError("the job stopped unexpectedly"))
