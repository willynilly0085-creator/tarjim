"""Run a vendor's program with a time limit that really ends it.

On Windows a time limit on subprocess.run kills only the program itself and then waits, with no
limit, for its output pipes, which a helper it started still holds (Codex: node runs codex.exe).
Here the prompt and the output go through files, so nothing waits on a pipe, and a program that
runs out of time is stopped together with everything it started.
"""
import subprocess
import sys
import tempfile
from typing import IO, Any

from tarjim.children import end, tree

HIDDEN = 0x08000000 if sys.platform == "win32" else 0


def text_of(file: IO[bytes]) -> str:
    file.seek(0)
    words = file.read().decode("utf-8", errors="replace")
    return words.replace("\r\n", "\n").replace("\r", "\n")


def bounded(command: list[str], given: str, seconds: float,
            **options: Any) -> subprocess.CompletedProcess[str]:
    """What the program printed; subprocess.TimeoutExpired once it ran out of time."""
    with tempfile.TemporaryFile() as prompt, tempfile.TemporaryFile() as out, \
            tempfile.TemporaryFile() as err:
        prompt.write(given.encode("utf-8"))
        prompt.seek(0)
        process = subprocess.Popen(command, stdin=prompt, stdout=out, stderr=err,
                                   creationflags=HIDDEN, **options)
        try:
            process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            end(tree(process))  # the whole family is found before any of it is killed
            process.kill()
            process.wait()
            raise
        return subprocess.CompletedProcess(command, process.returncode, text_of(out),
                                           text_of(err))
