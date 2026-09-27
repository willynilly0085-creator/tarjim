"""Translate with an AI subscription the person already has, through the vendor's own program."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tarjim.config import save, setting
from tarjim.engines.catalog import BY_ID, SUBSCRIPTION, of_method
from tarjim.engines.web import EngineError, parse_json, unwrap, wrap

TIMEOUT = 900
LONGEST_ARGUMENT = 24000
SHIM_TARGET = re.compile(r'"%dp0%\\([^"]+)"')
NOT_OFFERED = ("reserve", "review")
REFUSED = "not supported"
HIDDEN = 0x08000000 if sys.platform == "win32" else 0


def launcher(name: str) -> list[str]:
    found = shutil.which(f"{name}.cmd") or shutil.which(name)
    if not found or Path(found).suffix.lower() != ".cmd":
        return [found] if found else []
    targets = SHIM_TARGET.findall(Path(found).read_text(encoding="utf-8", errors="ignore"))
    if not targets:
        return []
    target = Path(found).parent / targets[-1]
    if target.suffix.lower() != ".js":
        return [str(target)]
    node = shutil.which("node")
    return [node, str(target)] if node else []


def installed() -> list[str]:
    return [p.id for p in of_method(SUBSCRIPTION) if launcher(p.program)]


def run(command: list[str], prompt: str, folder: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, input=prompt, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=TIMEOUT, cwd=folder,
                              creationflags=HIDDEN, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise EngineError(command[0], 0, str(error)) from error


def strict(schema: dict[str, Any]) -> dict[str, Any]:
    result = dict(schema)
    if result.get("type") == "object":
        result["properties"] = {k: strict(v) for k, v in result.get("properties", {}).items()}
        result["required"] = list(result["properties"])
        result["additionalProperties"] = False
    if isinstance(result.get("items"), dict):
        result["items"] = strict(result["items"])
    return result


class ClaudeAsker:
    hears = False

    def ask(self, prompt: str, _audio: bytes | None, schema: dict[str, Any]) -> Any:
        command = [*launcher("claude"), "-p", "--output-format", "json", "--tools", "",
                   "--json-schema", json.dumps(wrap(schema)), "--no-session-persistence",
                   "--setting-sources", "", "--strict-mcp-config"]
        if setting("claude_model"):
            command += ["--model", setting("claude_model")]
        with tempfile.TemporaryDirectory() as folder:
            done = run(command, prompt, folder)
        try:
            answer = json.loads(done.stdout or "{}")
        except ValueError as error:
            raise EngineError("claude", done.returncode, done.stderr or done.stdout) from error
        if answer.get("is_error") or "structured_output" not in answer:
            raise EngineError("claude", done.returncode, str(answer.get("result", done.stderr)))
        return unwrap(answer["structured_output"])


def codex_models() -> list[str]:
    cache = Path.home() / ".codex" / "models_cache.json"
    try:
        listed = json.loads(cache.read_text(encoding="utf-8")).get("models", [])
    except (OSError, ValueError, AttributeError):
        listed = []
    names = [str(m.get("slug") or m.get("id") or "") for m in listed if isinstance(m, dict)]
    offered = [n for n in names if n and not any(word in n for word in NOT_OFFERED)]
    saved = setting("codex_model")
    return [saved, *[n for n in offered if n != saved]] if saved else offered or [""]


class CodexAsker:
    hears = False

    def ask(self, prompt: str, _audio: bytes | None, schema: dict[str, Any]) -> Any:
        last = ""
        for model in codex_models():
            done, reply = self.once(prompt, schema, model)
            if done.returncode == 0 and reply:
                if model and model != setting("codex_model"):
                    save("codex_model", model)
                return unwrap(parse_json(reply))
            last = done.stderr[-400:]
            if REFUSED not in done.stderr:
                break
        raise EngineError("codex", 1, last)

    def once(self, prompt: str, schema: dict[str, Any],
             model: str) -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory() as folder:
            shape, reply = Path(folder) / "shape.json", Path(folder) / "reply.txt"
            shape.write_text(json.dumps(strict(wrap(schema))), encoding="utf-8")
            chosen = ["-m", model] if model else []
            command = [*launcher("codex"), "exec", *chosen, "--skip-git-repo-check", "--ephemeral",
                       "-s", "read-only", "-c", "notify=[]", "-c", "model_reasoning_effort=medium",
                       "--output-schema", str(shape), "-o", str(reply), "-"]
            done = run(command, prompt, folder)
            return done, reply.read_text(encoding="utf-8") if reply.exists() else ""


class PromptAsker:
    """Subscriptions whose program takes the prompt as an argument and answers in text."""

    hears = False

    def __init__(self, provider: str) -> None:
        self.provider = BY_ID[provider]

    def command(self, prompt: str) -> list[str]:
        model = setting(self.provider.model_name)
        chosen = [f"--model={model}"] if model else []
        quiet = ["-s"] if self.provider.id == "copilot" else []
        return [*launcher(self.provider.program), "-p", prompt, *quiet, *chosen]

    def ask(self, prompt: str, _audio: bytes | None, schema: dict[str, Any]) -> Any:
        shape = json.dumps(wrap(schema), ensure_ascii=False)
        full = f"{prompt}\n\nReply with only one JSON object matching this schema: {shape}"
        if len(full) > LONGEST_ARGUMENT:
            raise EngineError(self.provider.id, 0, "request too long for this program")
        with tempfile.TemporaryDirectory() as folder:
            done = run(self.command(full), "", folder)
        text = done.stdout.strip()
        start, end = text.find("{"), text.rfind("}")
        if done.returncode != 0 or start < 0:
            raise EngineError(self.provider.id, done.returncode, done.stderr or text)
        return unwrap(parse_json(text[start:end + 1]))


def subscription_asker(provider: str) -> Any:
    if provider == "claude":
        return ClaudeAsker()
    return CodexAsker() if provider == "codex" else PromptAsker(provider)
