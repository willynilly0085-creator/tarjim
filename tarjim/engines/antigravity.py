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

It also listens: shown an audio file in that folder, the model hears it through the program's
file viewer, with no terminal command (measured: six minutes of English and Arabic speech heard to
the last second in 48 s). Grok Build, Codex and Claude Code were given the same file and cannot.
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from tarjim.config import setting
from tarjim.engines.bounded import bounded
from tarjim.engines.reply_check import failed, program_reason
from tarjim.engines.subscription import launcher, run, strict
from tarjim.engines.web import EngineError, TimedOut, unwrap, wrap

PLAIN = ("--sandbox", "--disable-slash-commands")
# The effort is part of the model's id here. On a 24-line clip Flash (Low) took 10 s, (Medium)
# 88 s and (High) failed after 209 s, for the same Saudi translation: text is translated with the
# low variant of the chosen model whenever the account has one.
EFFORT = re.compile(r"-(medium|high|xhigh|max)$")
# An agent left to itself sometimes reaches for a terminal command, which headless mode refuses,
# and then answers nothing ("no output produced"); it is told plainly that none is needed.
DIRECT = ("Answer directly with the JSON asked for. Do not use any tool, file or terminal "
          "command: everything you need is in this message.\n\n")
LIGHTEST = ("flash", "-low")
LIST_SECONDS = 40
SIGN_IN = "sign in"
SOUND = "sound.mp3"
HEAR = (f"The audio to work on is the file {SOUND} in the current folder. Open it with your file "
        "viewer and listen to it; do not run any terminal command, script or program.\n\n")
NOT_SIGNED_IN = "not logged in: open Antigravity and sign in with your Google account"
# The account's models, kept once the program has listed some: a listing that failed or came
# back empty is asked again next time, and a fresh scan or a sign-in forgets them.
LISTED: list[tuple[str, str, str]] = []


class AntigravityAsker:
    hears = False

    def ask(self, prompt: str, audio: bytes | None, schema: dict[str, Any]) -> Any:
        """With audio, the program is shown the sound as a file: Gemini hears what it opens.
        Hearing uses the lightest model (measured on 94 s of speech: 16 s, against 446 s for the
        program's default). Either is tried again once, since the service sometimes answers 503
        or drops the answer halfway ("The stream was interrupted")."""
        if not audio:
            model = light_variant(setting("antigravity_model"))
            return self.twice(DIRECT + prompt, None, schema, model)
        return self.twice(HEAR + prompt, audio, schema, hearing_model())

    def twice(self, prompt: str, audio: bytes | None, schema: dict[str, Any], model: str) -> Any:
        try:
            return self.once(prompt, audio, schema, model)
        except TimedOut:
            raise  # after 15 minutes, a second try would only keep the job waiting as long
        except EngineError as error:
            if NOT_SIGNED_IN in str(error):
                raise
            return self.once(prompt, audio, schema, model)

    def once(self, prompt: str, audio: bytes | None, schema: dict[str, Any], model: str) -> Any:
        command = [*launcher("agy"), "--print", prompt, "--output-format", "json",
                   "--json-schema", json.dumps(strict(wrap(schema))), *PLAIN,
                   *(["--model", model] if model else [])]
        with tempfile.TemporaryDirectory() as folder:
            if audio:
                (Path(folder) / SOUND).write_bytes(audio)
            done = run(command, "", folder)
        return unwrap(answer_of(done.returncode, done.stdout, done.stderr, model))


def known_rows() -> list[tuple[str, str, str]]:
    if not LISTED:
        LISTED.extend(rows(listing()))
    return LISTED


def forget() -> None:
    LISTED.clear()


def light_variant(model: str) -> str:
    lighter = EFFORT.sub("-low", model)
    listed = {slug for slug, _name, _note in known_rows()} if lighter != model else set()
    return lighter if lighter in listed else model


def hearing_model() -> str:
    return suggested(known_rows()) or setting("antigravity_model")


def answer_of(code: int, printed: str, complaint: str, model: str = "") -> Any:
    """The structured answer from what the program printed; a sign-in problem is named as one."""
    try:
        answer = json.loads(printed[printed.find("{"):]) if "{" in printed else {}
    except ValueError:
        answer = {}
    if answer.get("status") == "SUCCESS" and "structured_output" in answer:
        return answer["structured_output"]
    # Only the program's own complaint can say it is signed out: a translation may say "sign in".
    # What it printed counts only when it is no JSON answer at all, so holds no translation.
    told = f"{answer.get('error') or ''} {complaint} {'' if answer else printed}".lower()
    if SIGN_IN in told or "authentication required" in told:
        raise EngineError("antigravity", code, NOT_SIGNED_IN)
    raise failed("antigravity", model, "no answer", program_reason(
        code, str(answer.get("error") or complaint or printed)))


def listing() -> str:
    """What `agy models` prints: the models this account can use, or a request to sign in."""
    program = launcher("agy")
    if not program:
        return ""
    try:
        done = bounded([*program, "models"], "", LIST_SECONDS)
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
