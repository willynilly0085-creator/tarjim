"""Chat tools that set tarjim up: everything the page can change, an assistant can change too.

Two things stay with the person on purpose. Keys and bot tokens are typed into tarjim's page, never
into a chat, so `open_tarjim_page` takes them there. And a browser extension asking to pair is
allowed by the person on the page, because that request must be answered by a human.
"""
import webbrowser
from typing import Any

from tarjim.assistant_http import SERVER, call
from tarjim.config import setting

SWITCH = {"yes": True, "no": False}
PLACES = {"": "", "setup": "#setup", "phone": "#phone"}
KEY_FIRST = "Then the person adds the key on tarjim's page: call open_tarjim_page."


def get_settings() -> Any:
    """Current settings: interface language, engines, which keys are set (never the keys),
    whether tarjim starts with the computer and updates by itself."""
    return call("/setup")


def change_settings(interface_language: str = "", listening_engine: str = "",
                    start_with_computer: str = "", automatic_updates: str = "") -> Any:
    """Change general settings. Leave a field empty to keep it.

    interface_language: a code from get_settings' ui_languages. listening_engine: gemini,
    openai or local. start_with_computer and automatic_updates: "yes" or "no".
    To change the translation engine or its model, use use_connection.
    """
    wanted: dict[str, Any] = {"ui_language": interface_language,
                              "listen_provider": listening_engine}
    switches = {"autostart": SWITCH.get(start_with_computer),
                "auto_update": SWITCH.get(automatic_updates)}
    body = {k: v for k, v in {**wanted, **switches}.items() if v not in ("", None)}
    return call("/setup", body)


def set_glossary(terms: str) -> Any:
    """Fix how names are translated, one per line "term = translation"; prefix a language
    code to limit a line to it ("ar: tarjim = ترجم"). Replaces the list; "" clears it."""
    return call("/setup", {"glossary": terms})


def plan_setup() -> Any:
    """Look at this computer (graphics card, tools, AI programs, subscriptions, saved keys) and
    return the setup tarjim suggests for it, with what each choice still needs. Changes nothing."""
    return call("/setup/plan?fresh=1")


def apply_setup(translate: dict[str, Any], listen: dict[str, Any],
                downloads: list[str] | None = None) -> Any:
    """Carry out a setup: save the translation and listening choices and start the downloads.

    translate and listen: the objects from plan_setup's "plan" (edit them first if the person
    wants something else). downloads: tool ids from list_tools to fetch now.
    """
    return call("/setup/apply", {"translate": translate, "listen": listen,
                                 "downloads": downloads or []})


def install_subscription_app(provider: str) -> Any:
    """Install the program a subscription needs (claude, codex, grok, antigravity, copilot),
    in the background. Then call sign_in so the person logs in."""
    return call("/connections/install-app", {"provider": provider})


def set_custom_api_address(url: str) -> Any:
    """The address of an OpenAI-compatible translation service, for the "custom" provider.
    Its key is added by the person on tarjim's page."""
    return call("/connections/address", {"url": url})


def start_local_ai(server: str) -> Any:
    """Start an AI program installed on this computer (ollama or lmstudio) without a window."""
    return call("/connections/start-local", {"server": server})


def find_local_ai() -> Any:
    """Search this computer for AI programs (Ollama, LM Studio, Jan, llama.cpp, KoboldCpp) that
    are installed but not on the usual paths. Takes up to twenty seconds."""
    return call("/connections/scan-local", {})


def list_models(provider: str) -> Any:
    """The models a provider offers this account, with the one tarjim suggests for translation."""
    return call("/connections/models", {"provider": provider})


def test_setup(language: str = "ar") -> Any:
    """Check that the current setup really works: the engines answer and a short line is
    translated into the language."""
    return call("/setup/selftest", {"language": language})


def list_voice_services() -> Any:
    """Dubbing voices that need the person's own key: which are linked, the services known by
    name (with the languages each speaks), and the model and voice names in use."""
    return call("/voices")


def use_voice_service(service: str, model: str = "", voices: str = "", address: str = "",
                      ) -> Any:
    """Choose the voice service for dubbing that speaks OpenAI's speech format.

    service: an id from list_voice_services' presets (openai, groq, openrouter, together), or
    "custom" with its address. model and voices (comma separated): leave empty to use the
    service's own for the language being dubbed. Gemini, ElevenLabs and Fish Audio need no
    choice here, only their key.
    """
    saved = call("/voices/speech", {"preset": service, "url": address, "model": model,
                                    "voices": voices})
    return {"saved": saved, "next": KEY_FIRST}


def prefer_elevenlabs_voice(voice_id: str) -> Any:
    """The ElevenLabs voice the first speaker gets (an id from list_voice_services); "" for
    no preference."""
    return call("/voices/eleven", {"voice": voice_id})


def phone_bot(language: str = "", result: str = "", dialect: str = "") -> Any:
    """The Telegram bot: its state, and what it sends back. Leave fields empty to only look.

    language: a code from list_languages. result: burn, srt, dub-gemini, dub-clone, dub-studio,
    dub-eleven, dub-elevenclone or dub-speech. dialect (Arabic): saudi or msa.
    Connecting a bot needs its token, which the person pastes on tarjim's page
    (open_tarjim_page with section "phone").
    """
    wanted = {"target": language, "mode": result, "dialect": dialect}
    chosen = {k: v for k, v in wanted.items() if v}
    return call("/phone/choices", chosen) if chosen else call("/phone")


def update_tarjim(install: bool = False) -> Any:
    """Is a newer tarjim out? With install=True, install it now (only when no job is running)."""
    return call("/update/apply", {}) if install else call("/update")


def open_tarjim_page(section: str = "") -> str:
    """Open tarjim's page in the browser, where the person adds keys and tokens safely.
    section: "" for the page, "setup" for setup, "phone" for the phone bot."""
    webbrowser.open(f"{setting('server') or SERVER}/{PLACES.get(section, '')}")
    return "Opened the tarjim page in the browser."


TOOLS = (get_settings, change_settings, set_glossary, plan_setup, apply_setup,
         install_subscription_app, set_custom_api_address, start_local_ai, find_local_ai,
         list_models, test_setup, list_voice_services,
         use_voice_service, prefer_elevenlabs_voice, phone_bot, update_tarjim, open_tarjim_page)


def attach(server: Any) -> None:
    for tool in TOOLS:
        server.tool()(tool)
