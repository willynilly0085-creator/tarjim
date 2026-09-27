"""tarjim as an MCP server: Claude or any MCP client can translate and adjust settings in chat."""
import json
import urllib.error
import urllib.request
import webbrowser
from typing import Any

from mcp.server.mcpserver import MCPServer

from tarjim.config import setting

SERVER = "http://127.0.0.1:17653"
OUTPUTS = {"subtitles": "srt", "burned": "burn", "dubbed": "dub"}
VOICES = ("clone", "studio", "fish", "fishvoice")

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
    return f"dub-{voice if voice in VOICES else 'clone'}" if mode == "dub" else mode


@tarjim.tool()
def translate_video(source: str, language: str = "ar", output: str = "burned",
                    voice: str = "clone") -> Any:
    """Translate a video from a link (YouTube, X, ...) or a local file path.

    language: target language code such as ar, en, fr, ja.
    output: "burned" (subtitles inside the video), "subtitles" (an .srt file) or "dubbed".
    voice (dubbing only): "clone" each speaker's own voice on this computer, "studio",
    "fish" cloning in the cloud, or "fishvoice" the calm Arabic narrator.
    """
    order = {"target": language, "mode": mode_for(output, voice), "dialect": "saudi"}
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
    """Pause, resume or cancel a running translation. action: pause, resume or cancel."""
    return call(f"/jobs/{job_id}/{action}", {})


@tarjim.tool()
def get_settings() -> Any:
    """Current settings: interface language, engines, which keys are set (never the keys)."""
    return call("/setup")


@tarjim.tool()
def change_settings(interface_language: str = "", listening_engine: str = "",
                    translation_engine: str = "", local_model: str = "") -> Any:
    """Change settings. Leave a field empty to keep it.

    interface_language: ar or en. listening_engine: gemini, openai or local.
    translation_engine: gemini, openai, anthropic or local.
    local_model: an Ollama model name for local translation, e.g. aya-expanse:8b.
    """
    wanted = {"ui_language": interface_language, "listen_provider": listening_engine,
              "translate_provider": translation_engine, "local_model": local_model}
    return call("/setup", {k: v for k, v in wanted.items() if v})


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
    tarjim.run(transport="stdio")


if __name__ == "__main__":
    main()
