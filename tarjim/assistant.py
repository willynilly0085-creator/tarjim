"""tarjim as an MCP server: Claude or any MCP client can translate and adjust settings in chat."""
import urllib.parse
from typing import Any

from mcp.server.mcpserver import MCPServer

from tarjim.assistant_http import call, fetch_text, wait_for
from tarjim.assistant_settings import attach
from tarjim.assistant_setup import install, start, status

OUTPUTS = {"subtitles": "srt", "burned": "burn", "dubbed": "dub"}
VOICES = ("natural", "clone", "studio", "fish", "fishvoice", "eleven", "elevenclone", "speech")
ACTIONS = ("pause", "resume", "cancel")
SUBTITLES = (".srt",)
MAX_WAIT = 240

tarjim = MCPServer("tarjim", instructions=(
    "tarjim is a tool on this computer that subtitles and dubs videos, any language to any "
    "language. Start with setup_status. You can change every setting with these tools. "
    "Never take API keys or bot tokens in chat: the person types them on tarjim's page, which "
    "open_tarjim_page opens."))


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
    voice (dubbing only): "natural" Gemini voices per speaker (default), "clone" the speaker's own
    voice on this computer, "studio", "fish" cloud cloning, "fishvoice" Arabic narrator, "eleven"
    ElevenLabs voices, "elevenclone" the speaker's voice there, "speech" a linked voice service.
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
def translation_status(job_id: str, wait_seconds: int = 0) -> Any:
    """One translation: stage, error, finished files. wait_seconds (up to 240) waits for
    the job to finish first, for assistants that cannot pause on their own."""
    return wait_for(job_id, max(0, min(wait_seconds, MAX_WAIT)))


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


@tarjim.tool()
def list_connections() -> Any:
    """Every way to connect an AI: API providers (key saved or not), subscriptions ("ready" means
    the app is installed, "signed_in" that it can be used now), plans, and AI programs on this
    computer with their models. Also shows which engine listens and which translates now."""
    return call("/connections")


@tarjim.tool()
def use_connection(provider: str, model: str = "", local_program: str = "") -> Any:
    """Translate with this provider from now on, optionally with a specific model.

    provider: an id from list_connections, or "local" for the AI on this computer.
    model: any model name the provider offers (leave empty for its default).
    local_program (with "local"): ollama, lmstudio, jan, llamacpp or koboldcpp.
    """
    wanted = {"provider": provider, "model": model, "server": local_program}
    return call("/connections/use", {k: v for k, v in wanted.items() if v})


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
    """Open the sign-in window of a subscription (claude, codex, grok, antigravity, copilot) so
    the person can log in with their own account."""
    return call("/connections/sign-in", {"provider": provider})


@tarjim.tool()
def setup_status() -> Any:
    """Is the tarjim engine on this computer running, installed but stopped, being installed,
    or missing? Call this first; it says what to do next."""
    return status()


@tarjim.tool()
def install_tarjim() -> Any:
    """Install and start the tarjim engine in the background (takes minutes). Then use
    setup_status, and open_tarjim_page so the person finishes setup in their browser."""
    return install()


@tarjim.tool()
def start_tarjim() -> Any:
    """Start the installed tarjim engine in the background, without any window."""
    return start()


@tarjim.tool()
def list_languages() -> Any:
    """Languages tarjim can translate into, with their codes."""
    return call("/languages")


attach(tarjim)


def main() -> None:
    from tarjim.quiet import hide_child_windows

    hide_child_windows()
    tarjim.run(transport="stdio")


if __name__ == "__main__":
    main()
