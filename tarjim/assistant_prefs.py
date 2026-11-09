"""Chat tools for the person's own settings (2026-11-09): how subtitles look, read and are
timed, how a clip is heard and translated, where files go, how a dub sounds. The same routes
as tarjim's settings page, so every value passes the same gate and a refused one comes back
with its Arabic reason. Descriptions stay short: get_preferences returns the table itself."""
import urllib.parse
from typing import Any

from tarjim.assistant_http import call

Output = str | dict[str, Any]


def get_preferences(group: str = "", language: str = "") -> Any:
    """The settings: each one's key, Arabic label, kind, range or choices and current value,
    what differs from the original, and the presets. group: look, text, timing, listen,
    translate, output or dub ("" for all); "fonts" lists the fonts that write the language.
    language: the target language code for per-language settings (default ar)."""
    lang = urllib.parse.quote(language or "ar")
    if group == "fonts":
        return call(f"/prefs/fonts?lang={lang}")
    return call(f"/prefs?lang={lang}&group={urllib.parse.quote(group)}")


def change_preferences(changes: dict[str, Any], language: str = "") -> Any:
    """Save settings, {key: value} with keys from get_preferences, such as
    {"look.size_wide": 110, "look.style": "outline"}. Answers saved, refused {key: reason}
    and notes. language: for per-language settings (font, reading speed, line length)."""
    return call("/prefs", {"values": changes, "language": language or "ar"})


def reset_preferences(what: str = "all", language: str = "") -> Any:
    """Put settings back to the original: "all", a group (look, text, timing...) or one key.
    With language, a per-language setting goes back for that language only; shared ones in
    the scope still go back for every language."""
    return call("/prefs/reset", {"what": what, "language": language})


def use_preset(name: str, save_current: bool = False) -> Any:
    """Apply a preset: original, calm, news, bold, phone, easy, verbatim, or one of the
    person's own (get_preferences lists them). save_current=True instead keeps the current
    settings under this name (up to 10)."""
    return call("/prefs/preset", {"save_as" if save_current else "name": name})


def split_output(output: Output) -> tuple[str, dict[str, Any]]:
    """translate_video's output, and the settings for that one video when it is an object:
    {"result": "burned", "tweaks": {"look.size_wide": 110}}."""
    if not isinstance(output, dict):
        return output or "burned", {}
    tweaks = output.get("tweaks") or {}
    # Anything but an object goes on as it is, so the server refuses it with its reason.
    return str(output.get("result") or "burned"), tweaks if isinstance(tweaks, dict) else {
        "tweaks": tweaks}


TOOLS = (get_preferences, change_preferences, reset_preferences, use_preset)


def attach(server: Any) -> None:
    for tool in TOOLS:
        server.tool()(tool)
