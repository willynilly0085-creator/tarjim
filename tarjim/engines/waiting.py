"""A subscription program started ahead of the question, for the text a person selects.

Asked the usual way (antigravity.py), Google's program is started for every question. Measured
on 2026-11-16 for two sentences: two seconds to start, two more for the extra step that puts the
answer in the schema's shape, and around them the model's own time (Gemini 4 Hydrogen: High 8 s,
Medium 5 s, Low 2.6 s). Here one program waits, already started, in an empty folder. It is given
one question, its answer is read as it prints it, and it is ended; the next one is started
behind the answer. So no two questions share a conversation, and nothing a person selected is
remembered. A waiting program holds memory (177 MB measured), so one nobody asked for five
minutes is ended, and the question after that waits for a start.
"""
import atexit
import queue
import subprocess
import tempfile
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import IO, Any

from tarjim.children import end, tree
from tarjim.engines.bounded import HIDDEN
from tarjim.engines.web import EngineError, TimedOut

IDLE = 300.0
ANSWER = 180.0
Lines = queue.Queue[str | None]


@dataclass(frozen=True)
class Kind:
    """How one vendor's program waits: its command (light or as picked), a question as the line
    it reads, and the answer in a line it prints (None while the answer is still coming)."""
    command: Callable[[bool], list[str]]
    question: Callable[[str], str]
    spoken: Callable[[str], Any]


@dataclass(eq=False)
class Held:
    command: list[str]
    program: subprocess.Popen[str]
    folder: tempfile.TemporaryDirectory[str]
    lines: Lines
    idle: threading.Timer | None = None


def pump(pipe: IO[str], lines: Lines) -> None:
    for line in pipe:
        lines.put(line)
    lines.put(None)


def started(command: list[str]) -> Held:
    folder = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    program = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        cwd=folder.name, text=True, encoding="utf-8", errors="replace", creationflags=HIDDEN)
    lines: Lines = queue.Queue()
    assert program.stdout is not None
    threading.Thread(target=pump, args=(program.stdout, lines), daemon=True).start()
    return Held(command, program, folder, lines)


def ended(held: Held) -> None:
    """The program and everything it started are stopped, and its folder removed."""
    if held.idle:
        held.idle.cancel()
    end(tree(held.program))
    held.program.kill()
    held.program.wait()
    for pipe in (held.program.stdin, held.program.stdout):
        if pipe:
            pipe.close()
    held.folder.cleanup()


def answer_in(lines: Lines, spoken: Callable[[str], Any]) -> Any:
    deadline = time.monotonic() + ANSWER
    while True:
        try:
            line = lines.get(timeout=max(0.0, deadline - time.monotonic()))
        except queue.Empty as error:
            raise TimedOut("waiting", 0, "no answer in time") from error
        if line is None:
            raise EngineError("waiting", 0, "the program ended without an answer")
        found = spoken(line)
        if found is not None:
            return found


class Waiting:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.held: Held | None = None

    def taken(self, command: list[str]) -> Held | None:
        """The waiting program, when it still runs and was started with this command."""
        with self.lock:
            held, self.held = self.held, None
        if held and held.command == command and held.program.poll() is None:
            if held.idle:
                held.idle.cancel()
            return held
        if held:
            ended(held)
        return None

    def ready(self, command: list[str]) -> None:
        """Start the next one, unless one already waits."""
        with self.lock:
            if self.held is not None:
                return
            self.held = held = started(command)
            held.idle = threading.Timer(IDLE, self.retire, [held])
            held.idle.daemon = True
            held.idle.start()

    def retire(self, held: Held | None = None) -> None:
        """End the waiting program: the one named, once nobody asked it in time, or any."""
        with self.lock:
            waiting = self.held
            if waiting is None or (held is not None and waiting is not held):
                return
            self.held = None
        ended(waiting)

    def ask(self, kind: Kind, prompt: str, light: bool) -> Any:
        command = kind.command(light)
        held = self.taken(command) or started(command)
        threading.Thread(target=self.ready, args=(command,), daemon=True).start()
        try:
            assert held.program.stdin is not None
            held.program.stdin.write(kind.question(prompt) + "\n")
            held.program.stdin.flush()
            return answer_in(held.lines, kind.spoken)
        finally:  # behind the answer: stopping a program and its folder took over a second
            threading.Thread(target=ended, args=(held,), daemon=True).start()


WAITING = Waiting()
atexit.register(WAITING.retire)


def kinds() -> dict[str, Kind]:
    from tarjim.engines import antigravity

    return {"antigravity": Kind(antigravity.waiting_command, antigravity.question,
                                antigravity.spoken)}


def answer(provider: str, prompt: str, light: bool) -> Any:
    """None when this engine has no waiting program, or the waiting one failed: the engine is
    then asked the usual way, which names what went wrong. The log gets the kind of failure
    only: an error's words can hold what the person selected."""
    kind = kinds().get(provider)
    if not kind or not kind.command(light):
        return None
    try:
        return WAITING.ask(kind, prompt, light)
    except (EngineError, OSError, ValueError) as error:
        print(f"selected text: the waiting {provider} gave no answer ({type(error).__name__}); "
              "asking it the usual way", flush=True)
        return None
