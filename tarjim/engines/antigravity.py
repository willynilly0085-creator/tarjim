"""Translate with a Google account's Gemini (Google AI Pro or Ultra, or the allowance every account
has) through Google's own program, Antigravity CLI (`agy`). Google moved personal accounts here
from Gemini CLI on 2026-06-18.

The program is asked one question, sandboxed, in an empty folder that is deleted afterwards, and
answers in the JSON shape tarjim asks for. Without a terminal it denies every shell command by
itself and can write only inside that folder. Plan mode is not used: measured, it writes a plan
file first and takes four times as long (38 s against 9 s for six lines). `agy models` gives the
sign-in state and the models this account can use, each as an id, a tab and a name. The lightest
model is suggested: the "high" one took 43 s for two lines. Its flags follow `agy --help` of
version 1.3.2.
"""
import json
import subprocess
import tempfile
from typing import Any

from tarjim.config import setting
from tarjim.engines.subscription import HIDDEN, launcher, run, strict
from tarjim.engines.web import EngineError, unwrap, wrap

PLAIN = ("--sandbox", "--disable-slash-commands")
LIGHTEST = ("flash", "-low")
LIST_SECONDS = 40
SIGN_IN = "sign in"
NOT_SIGNED_IN = "not logged in: open Antigravity and sign in with your Google account"


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


def suggested(found: list[tuple[str, str, str]]) -> str:
    fitting = [slug for slug, _name, _note in found if all(mark in slug for mark in LIGHTEST)]
    return fitting[0] if fitting else ""


def rows(text: str) -> list[tuple[str, str, str]]:
    """Each line of the listing is a model's id, a tab, and its name; none while signed out."""
    pairs = [line.split("\t", 1) for line in text.splitlines() if "\t" in line]
    return [(slug.strip(), name.strip(), "") for slug, name in pairs if slug.strip()]
