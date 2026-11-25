"""Translate with a GitHub Copilot subscription through GitHub's own program, Copilot CLI.

The transcript in the prompt is a stranger's text, so the model is shown no tool at all. Measured
with Copilot CLI 1.0.115 against a local stand-in for the model, which logged every request: the
command tarjim used before sent 18 tools (bash, web_fetch, view, task...) with each question;
with `--available-tools=` it sends none. The `=` matters: a bare `--available-tools` followed by
another flag is ignored and every tool stays. The deny rules are a second lock behind it, and
win over every allow (`copilot help permissions`).
"""
import json
import tempfile
from typing import Any

from tarjim.config import setting
from tarjim.engines.catalog import BY_ID
from tarjim.engines.reply_check import failed, program_reason
from tarjim.engines.subscription import LONGEST_ARGUMENT, launcher, run
from tarjim.engines.web import EngineError, parse_json, unwrap, wrap

NO_TOOLS = ("--available-tools=", "--deny-tool", "shell", "--deny-tool", "write",
            "--deny-tool", "read", "--deny-tool", "url", "--deny-tool", "memory",
            "--disable-builtin-mcps", "--no-custom-instructions", "--no-ask-user",
            "--disallow-temp-dir")
TOO_OLD = "this Copilot cannot run without its tools; update it: npm install -g @github/copilot"


def command(prompt: str) -> list[str]:
    model = setting(BY_ID["copilot"].model_name)
    chosen = [f"--model={model}"] if model else []
    return [*launcher("copilot"), "-p", prompt, "--output-format", "json", *NO_TOOLS, *chosen]


def reply_text(stdout: str) -> str:
    """The last whole message of the answer, from Copilot's one-event-per-line output."""
    said = ""
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "assistant.message":
            said = str((event.get("data") or {}).get("content") or "")
    return said


def complaint(stderr: str, stdout: str) -> str:
    return TOO_OLD if "unexpected argument '--" in stderr else stderr or stdout[-400:]


class CopilotAsker:
    hears = False

    def ask(self, prompt: str, _audio: bytes | None, schema: dict[str, Any]) -> Any:
        shape = json.dumps(wrap(schema), ensure_ascii=False)
        full = f"{prompt}\n\nReply with only one JSON object matching this schema: {shape}"
        if len(full) > LONGEST_ARGUMENT:
            raise EngineError("copilot", 0, "request too long for this program")
        with tempfile.TemporaryDirectory() as folder:
            done = run(command(full), "", folder)
        text = reply_text(done.stdout)
        if done.returncode != 0 or "{" not in text:
            said = complaint(done.stderr, done.stdout)
            raise failed("copilot", setting(BY_ID["copilot"].model_name), "no answer",
                         program_reason(done.returncode, said))
        return unwrap(parse_json(text))
