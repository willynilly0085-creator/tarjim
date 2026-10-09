"""Translate with a Google account's Gemini (Google AI Pro or Ultra, or the allowance every account
has) through Google's own program, Antigravity CLI (`agy`). Google moved personal accounts here
from Gemini CLI on 2026-06-18.

The program is asked one question in plan mode (it may read, never change), sandboxed, in an empty
folder, and answers in the JSON shape tarjim asks for. `agy models` gives both the sign-in state
and the models this account can use. Its flags follow `agy --help` of version 1.3.2.
"""
import json
import re
import subprocess
import tempfile
from typing import Any

from tarjim.config import setting
from tarjim.engines.subscription import HIDDEN, launcher, run, strict
from tarjim.engines.web import EngineError, unwrap, wrap

PLAIN = ("--mode", "plan", "--sandbox", "--disable-slash-commands")
LIST_SECONDS = 40
SIGN_IN = "sign in"
NOT_SIGNED_IN = "not logged in: open Antigravity and sign in with your Google account"
LISTED = re.compile(r"^\s*(?:[*•-]\s+)?([a-z][\w.:-]*\d[\w.:-]*)\b(.*)$", re.MULTILINE)


class AntigravityAsker:
    hears = False

    def ask(self, prompt: str, _audio: bytes | None, schema: dict[str, Any]) -> Any:
        model = setting("antigravity_model")
        command = [*launcher("agy"), "--print", prompt, "--output-format", "json",
                   "--json-schema", json.dumps(strict(wrap(schema))), *PLAIN,
                   *(["--model", model] if model else [])]
        with tempfile.TemporaryDirectory() as folder:
            done = run(command, "", folder)
        return unwrap(answer_of(done.returncode, done.stdout, done.stderr))


def answer_of(code: int, printed: str, complaint: str) -> Any:
    """The structured answer from what the program printed; a sign-in problem is named as one."""
    try:
        answer = json.loads(printed[printed.find("{"):]) if "{" in printed else {}
    except ValueError:
        answer = {}
    problem = str(answer.get("error") or complaint or printed)
    if SIGN_IN in problem.lower() or "authentication required" in problem.lower():
        raise EngineError("antigravity", code, NOT_SIGNED_IN)
    if answer.get("status") != "SUCCESS" or "structured_output" not in answer:
        raise EngineError("antigravity", code, problem)
    return answer["structured_output"]


def listing() -> str:
    """What `agy models` prints: the models this account can use, or a request to sign in."""
    program = launcher("agy")
    if not program:
        return ""
    try:
        done = subprocess.run([*program, "models"], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=LIST_SECONDS,
                              stdin=subprocess.DEVNULL, creationflags=HIDDEN, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout


def rows(text: str) -> list[tuple[str, str, str]]:
    """Model ids from the listing, in the program's own order; none while signed out."""
    if SIGN_IN in text.lower():
        return []
    return [(name, "", "") for name, _rest in LISTED.findall(text)]
