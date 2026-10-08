"""Translate with a Grok subscription (SuperGrok, X Premium+) through xAI's own program, Grok Build.

The program is asked one question with no tools, no web search and no sub-agents, and answers in
the JSON shape tarjim asks for. Its flags follow `grok --help` of version 1.0.46.
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from tarjim.config import setting
from tarjim.engines.subscription import HIDDEN, launcher, run, strict
from tarjim.engines.web import EngineError, unwrap, wrap

PLAIN = ("--tools", "", "--disable-web-search", "--no-subagents", "--no-plan", "--max-turns", "1")
LISTED = re.compile(r"^\s*[*-]\s+([\w.:-]+)(\s+\(default\))?\s*$", re.MULTILINE)
LIST_SECONDS = 30


class GrokAsker:
    hears = False

    def ask(self, prompt: str, _audio: bytes | None, schema: dict[str, Any]) -> Any:
        model = setting("grok_model")
        with tempfile.TemporaryDirectory() as folder:
            question = Path(folder) / "prompt.txt"
            question.write_text(prompt, encoding="utf-8")
            command = [*launcher("grok"), "--prompt-file", str(question), "--output-format", "json",
                       "--json-schema", json.dumps(strict(wrap(schema))), *PLAIN,
                       *(["-m", model] if model else [])]
            done = run(command, "", folder)
        try:
            answer = json.loads(done.stdout or "{}")
        except ValueError as error:
            raise EngineError("grok", done.returncode, done.stderr or done.stdout) from error
        if done.returncode != 0 or "structuredOutput" not in answer:
            raise EngineError("grok", done.returncode, done.stderr or str(answer.get("text", "")))
        return unwrap(answer["structuredOutput"])


def listing() -> str:
    """What `grok models` prints: the sign-in state, then the models this account can use."""
    program = launcher("grok")
    if not program:
        return ""
    try:
        done = subprocess.run([*program, "models"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=LIST_SECONDS,
                              creationflags=HIDDEN, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout if done.returncode == 0 else ""


def grok_rows(text: str) -> list[tuple[str, str, str]]:
    """Model ids from the listing, the account's default first, for the model catalog."""
    found = LISTED.findall(text)
    return [(name, "", "") for name, _default in sorted(found, key=lambda row: not row[1])]


def signed_in(text: str) -> bool:
    lowered = text.lower()
    return "logged in" in lowered and "not logged in" not in lowered
