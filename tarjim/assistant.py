"""tarjim as an MCP server: Claude or any MCP client can translate and adjust settings in chat."""
import json
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from typing import Any

from mcp.server.mcpserver import MCPServer

from tarjim.config import setting

SERVER = "http://127.0.0.1:17653"
OUTPUTS = {"subtitles": "srt", "burned": "burn", "dubbed": "dub"}
VOICES = ("natural", "clone", "studio", "fish", "fishvoice")
ACTIONS = ("pause", "resume", "cancel")
SUBTITLES = (".srt",)

tarjim = MCPServer("tarjim", instructions=(
    "tarjim translates videos into subtitles or dubbing on this computer. Use translate_video "
    "with a link or a local file path, then translation_status to follow it. API keys are never "
    "set through chat: send the person to open_tarjim_page for keys."))


def call(path: str, body: dict[str, Any] | None = None) -> Any:
    request = urllib.request.Request(
        f"{setting('server') or SERVER}{path}", method="POST" if body is not None else "GET",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"X-Tarjim-Token": setting("token"), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as reply:
            return json.loads(reply.read() or b"null")
    except urllib.error.HTTPError as error:
        return {"error": error.code, "detail": error.read().decode("utf-8", "replace")[:200]}
    except urllib.error.URLError:
        return {"error": "tarjim is not running on this computer. Start it with: tarjim-serve"}


def mode_for(output: str, voice: str) -> str:
    mode = OUTPUTS.get(output, "burn")
    chosen = {"natural": "gemini"}.get(voice, voice if voice in VOICES else "gemini")
    return f"dub-{chosen}" if mode == "dub" else mode


@tarjim.tool()
def translate_video(source: str, language: str = "ar", output: str = "burned",
                    voice: str = "natural") -> Any:
    """Translate a video from a link (YouTube, X, ...) or a local file path.

    language: target language code such as ar, en, fr, ja. Arabic is Saudi by default;
    use "ar-msa" for Modern Standard Arabic.
    output: "burned" (subtitles inside the video), "subtitles" (an .srt file) or "dubbed".
    voice (dubbing only): "natural" lifelike Gemini voices matched to each speaker (default),
    "clone" each speaker's own voice on this computer, "studio",
    "fish" cloning in the cloud, or "fishvoice" the calm Arabic narrator.
    """
    target, _, dialect = language.partition("-")
    order = {"target": target, "mode": mode_for(output, voice),
             "dialect": "msa" if dialect == "msa" else "saudi"}
    if source.lower().startswith(("http://", "https://")):
        return call("/jobs", {"url": source, **order})
    return call("/jobs/local", {"path": source, **order})


@tarjim.tool()
def list_translations() -> Any:
    """Recent translations with their stage (queued, hearing, timing, translating, done...)."""
    return call("/jobs")


@tarjim.tool()
def translation_status(job_id: str) -> Any:
    """One translation: its stage, any error, and the full paths of the finished files."""
    return call(f"/jobs/{job_id}")


@tarjim.tool()
def control_translation(job_id: str, action: str) -> Any:
    """Pause, resume or cancel a running translation, or retry one that failed or was
    cancelled. action: pause, resume, cancel or retry."""
    if action == "retry":
        return call(f"/retry/{job_id}", {})
    if action not in ACTIONS:
        return {"error": "action must be pause, resume, cancel or retry"}
    return call(f"/jobs/{job_id}/{action}", {})


@tarjim.tool()
def open_result(job_id: str, how: str = "play") -> Any:
    """Open a finished translation on this computer. how: "play" the video, or "folder" to
    show it in its folder."""
    return call(f"/{'reveal' if how == 'folder' else 'open'}/{job_id}", {})


@tarjim.tool()
def read_subtitles(job_id: str) -> Any:
    """The translated subtitles of a finished job as SRT text, to review or quote them."""
    job = call(f"/jobs/{job_id}")
    files = job.get("files", []) if isinstance(job, dict) else []
    names = [str(f).replace("\\", "/").rsplit("/", 1)[-1] for f in files]
    wanted = [n for n in names if n.endswith(SUBTITLES)]
    if not wanted:
        return {"error": "no subtitles yet", "job": job}
    return fetch_text(f"/files/{job_id}/{urllib.parse.quote(wanted[0])}")


def fetch_text(path: str) -> Any:
    request = urllib.request.Request(f"{setting('server') or SERVER}{path}",
                                     headers={"X-Tarjim-Token": setting("token")})
    try:
        with urllib.request.urlopen(request, timeout=30) as reply:
            return reply.read().decode("utf-8-sig", "replace")
    except urllib.error.URLError as error:
        return {"error": str(error)}


@tarjim.tool()
def get_settings() -> Any:
    """Current settings: interface language, engines, which keys are set (never the keys)."""
    return call("/setup")


@tarjim.tool()
def change_settings(interface_language: str = "", listening_engine: str = "",
                    translation_engine: str = "", local_model: str = "") -> Any:
    """Change settings. Leave a field empty to keep it.

    interface_language: ar or en. listening_engine: gemini, openai or local.
    translation_engine: any id from list_connections: an API provider (gemini, openai,
    anthropic, openrouter, deepseek, qwen, mistral, groq, xai, custom), a subscription
    (claude, codex, copilot, antigravity) or local.
    local_model: the model name for local translation, e.g. aya-expanse:8b.
    """
    wanted = {"ui_language": interface_language, "listen_provider": listening_engine,
              "translate_provider": translation_engine, "local_model": local_model}
    return call("/setup", {k: v for k, v in wanted.items() if v})


@tarjim.tool()
def list_connections() -> Any:
    """Every way to connect an AI and whether it is ready: API providers (key saved or not),
    subscriptions (app installed or not), and AI programs running on this computer with their
    models. Also shows which engine listens and which translates now."""
    return call("/connections")


@tarjim.tool()
def use_connection(provider: str, model: str = "") -> Any:
    """Translate with this provider from now on, optionally with a specific model.

    provider: an id from list_connections, or "local" for the AI on this computer.
    model: any model name the provider offers (leave empty for its default).
    """
    return call("/connections/use", {"provider": provider, "model": model})


@tarjim.tool()
def list_tools() -> Any:
    """Programs and models tarjim uses (ffmpeg, local listening, voices...) and whether each
    is installed."""
    return call("/tools")


@tarjim.tool()
def install_tool(tool_id: str) -> Any:
    """Download and install one tool from list_tools, in the background."""
    return call(f"/tools/{tool_id}", {})


@tarjim.tool()
def sign_in(provider: str) -> Any:
    """Open the sign-in window of a subscription (claude, codex, copilot, antigravity) so the
    person can log in with their own account."""
    return call("/connections/sign-in", {"provider": provider})


@tarjim.tool()
def list_languages() -> Any:
    """Languages tarjim can translate into, with their codes."""
    return call("/languages")


@tarjim.tool()
def open_tarjim_page() -> str:
    """Open the tarjim page in the browser, where keys and tools are managed safely."""
    webbrowser.open(f"{setting('server') or SERVER}/")
    return "Opened the tarjim page in the browser."


def main() -> None:
    from tarjim.quiet import hide_child_windows

    hide_child_windows()
    tarjim.run(transport="stdio")


if __name__ == "__main__":
    main()
