"""Translate with an AI subscription the person already has, through the vendor's own program."""
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from tarjim.config import save, setting
from tarjim.engines import own_node, programs
from tarjim.engines.bounded import bounded
from tarjim.engines.catalog import BY_ID, SUBSCRIPTION, of_method
from tarjim.engines.reply_check import Reason, failed, program_reason
from tarjim.engines.web import EngineError, TimedOut, parse_json, unwrap, wrap

TIMEOUT = 900
LONGEST_ARGUMENT = 24000
SHIM_TARGET = re.compile(r'"%dp0%\\([^"]+)"')
NOT_OFFERED = ("reserve", "review")
# The transcript is a stranger's text and a translation needs no tool. Per `codex exec --help`
# 0.162.1 the person's config.toml (MCP servers, plugins) and .rules files stay out while "auth
# still uses `CODEX_HOME`". Tools are switched off as `-c features.<name>=false`, which a Codex
# that lacks a name ignores (`--disable <name>` refuses it and would stop every translation).
NO_TOOLS = ("shell_tool", "view_image", "apps", "plugins", "hooks", "computer_use", "browser_use",
            "browser_use_external", "in_app_browser", "multi_agent", "image_generation",
            "skill_mcp_dependency_install", "tool_suggest")
ALONE = ("--ignore-user-config", "--ignore-rules",
         *[part for name in NO_TOOLS for part in ("-c", f"features.{name}=false")])
TOO_OLD = "this Codex cannot run without its tools; update it: npm install -g @openai/codex"
REFUSED = "not supported"


OWN_FOLDERS = (Path(".local") / "bin", Path(".grok") / "bin",
               Path("AppData") / "Local" / "agy" / "bin")


def own_folder(name: str) -> str | None:
    """Where vendors' own installers, or tarjim's own Node.js, put a program not on PATH yet."""
    places = [Path.home() / folder / file for folder in OWN_FOLDERS
              for file in (f"{name}.exe", name)]
    return next((str(p) for p in places if p.is_file()), None) or own_node.shim(name)


def launcher(name: str) -> list[str]:
    found = programs.find(f"{name}.cmd") or programs.find(name) or own_folder(name)
    if not found or Path(found).suffix.lower() != ".cmd":
        return [found] if found else []
    targets = SHIM_TARGET.findall(Path(found).read_text(encoding="utf-8", errors="ignore"))
    if not targets:
        return []
    target = Path(found).parent / targets[-1]
    if target.suffix.lower() != ".js":
        return [str(target)]
    node = programs.find("node") or own_node.node()
    return [node, str(target)] if node else []


def installed() -> list[str]:
    return [p.id for p in of_method(SUBSCRIPTION) if launcher(p.program)]


def run(command: list[str], prompt: str, folder: str,
        env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return bounded(command, prompt, TIMEOUT, cwd=folder, env=env)
    except subprocess.TimeoutExpired as error:
        raise TimedOut(command[0], 0, str(error)) from error
    except OSError as error:
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
        model = setting("claude_model")
        try:
            answer = json.loads(done.stdout or "{}")
        except ValueError as error:
            raise failed("claude", model, "no answer", program_reason(
                done.returncode, done.stderr or done.stdout)) from error
        if answer.get("is_error") or "structured_output" not in answer:
            said = f"{answer.get('subtype') or ''} {answer.get('result') or done.stderr}"
            raise failed("claude", model, "no answer", program_reason(done.returncode, said))
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


def outdated(stderr: str) -> str:
    """A Codex older than `--ignore-user-config` is told to update, never run with the
    person's own tools and servers."""
    return TOO_OLD if "unexpected argument '--ignore" in stderr else stderr[-400:]


class CodexAsker:
    hears = False

    def ask(self, prompt: str, _audio: bytes | None, schema: dict[str, Any]) -> Any:
        last, tried, code = "", "", 1
        for model in codex_models():
            done, reply = self.once(prompt, schema, model)
            if done.returncode == 0 and reply:
                if model and model != setting("codex_model"):
                    save("codex_model", model)
                return unwrap(parse_json(reply))
            last, tried, code = outdated(done.stderr), model, done.returncode
            if REFUSED not in done.stderr:
                break
        raise failed("codex", tried, "no answer", Reason(detail=f"exit code {code}; {last}"))

    def once(self, prompt: str, schema: dict[str, Any],
             model: str) -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory() as folder:
            shape, reply = Path(folder) / "shape.json", Path(folder) / "reply.txt"
            shape.write_text(json.dumps(strict(wrap(schema))), encoding="utf-8")
            chosen = ["-m", model] if model else []
            command = [*launcher("codex"), "exec", *chosen, "--skip-git-repo-check", "--ephemeral",
                       "-s", "read-only", *ALONE, "-c", "notify=[]",
                       "-c", "model_reasoning_effort=medium",
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
            raise failed(self.provider.id, setting(self.provider.model_name), "no answer",
                         program_reason(done.returncode, done.stderr or text))
        return unwrap(parse_json(text[start:end + 1]))


def subscription_asker(provider: str) -> Any:
    if provider == "claude":
        return ClaudeAsker()
    if provider == "grok":
        from tarjim.engines.grok import GrokAsker

        return GrokAsker()
    if provider == "antigravity":
        from tarjim.engines.antigravity import AntigravityAsker

        return AntigravityAsker()
    return CodexAsker() if provider == "codex" else PromptAsker(provider)
