"""What actually went wrong, safe to show: every failure carries its real reason, with anything
that looks like a key or token masked and the person's home folder shortened."""
import re
from pathlib import Path

SECRET = re.compile(r"[A-Za-z0-9_\-]{24,}")
LIMIT = 220


def evidence(error: str) -> str:
    line = next((part.strip() for part in error.splitlines() if part.strip()), "")
    line = line.replace(str(Path.home()), "~")
    line = SECRET.sub("***", line)
    return line if len(line) <= LIMIT else line[:LIMIT - 1] + "…"
