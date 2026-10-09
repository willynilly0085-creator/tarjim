"""Turn what the scan found into one setup plan, the way a person who knows the options would.

Translation: a subscription already signed in, then a saved key, then an AI program on this
computer with a model (only with a graphics card), then the free Gemini key.
Listening: a saved key that can hear, then the same Gemini key when translation needs it anyway,
then this computer's graphics card, then the free Gemini key.
"""
import re
from typing import Any

SUBSCRIPTION_ORDER = ("claude", "codex", "grok", "antigravity", "copilot")
KEY_ORDER = ("gemini", "openai", "anthropic", "openrouter", "deepseek", "qwen", "mistral", "groq",
             "xai", "opencode", "opencode_go", "kimi", "glm", "minimax")
HEARS = ("gemini", "openai")
MODEL_PREFERENCE = ("aya", "qwen", "gemma", "llama", "mistral")
TOO_BIG = re.compile(r"[:-](\d{2,3})b\b")
BIG_MODEL_B = 30
LOCAL_VRAM = 8.0
SPARE_GB = 2.0
Plan = dict[str, Any]


def too_big(model: str) -> bool:
    size = TOO_BIG.search(model)
    return size is not None and int(size.group(1)) >= BIG_MODEL_B


def pick_model(models: list[str]) -> str:
    fitting = [m for m in models if not too_big(m)]
    for family in MODEL_PREFERENCE:
        found = next((m for m in fitting if family in m.lower()), "")
        if found:
            return found
    return fitting[0] if fitting else ""


def local_choice(scan: Plan) -> Plan | None:
    if scan["device"]["vram_gb"] < LOCAL_VRAM:
        return None
    for program in scan["local"]["programs"]:
        model = pick_model(program.get("models", []))
        if model and (program["running"] or program.get("can_start")):
            return {"provider": "local", "server": program["id"], "model": model,
                    "reason": "local", "ready": bool(program["running"])}
    return None


def translate_choice(scan: Plan) -> Plan:
    signed = {a["id"] for a in scan["subscriptions"]["apps"] if a["signed_in"]}
    subscription = next((p for p in SUBSCRIPTION_ORDER if p in signed), "")
    if subscription:
        return {"provider": subscription, "reason": "signed_in", "ready": True}
    key = next((p for p in KEY_ORDER if p in scan["keys"]["saved"]), "")
    if key:
        return {"provider": key, "reason": "key", "ready": True}
    return local_choice(scan) or {"provider": "gemini", "reason": "free_key", "ready": False}


def listen_choice(scan: Plan, translate: Plan) -> Plan:
    key = next((p for p in HEARS if p in scan["keys"]["saved"]), "")
    if key:
        return {"provider": key, "reason": "key", "ready": True}
    if translate["provider"] == "gemini":
        return {"provider": "gemini", "reason": "same_key", "ready": False}
    if scan["device"]["gpu"]:
        ready = scan["tools"]["installed"]["accuracy"]
        return {"provider": "local", "reason": "gpu", "ready": ready}
    return {"provider": "gemini", "reason": "no_gpu", "ready": False}


def needs(translate: Plan, listen: Plan) -> list[Plan]:
    wanted: list[Plan] = []
    if "gemini" in (translate["provider"], listen["provider"]) and not (
            translate["ready"] and listen["ready"]):
        wanted.append({"kind": "key", "provider": "gemini"})
    if translate["provider"] == "local" and not translate["ready"]:
        wanted.append({"kind": "start_local", "server": translate["server"]})
    return wanted


def missing(scan: Plan, listen: Plan) -> list[str]:
    wanted = ["ffmpeg", "timing"] + (["accuracy"] if listen["provider"] == "local" else [])
    return [tool for tool in wanted if not scan["tools"]["installed"][tool]]


def downloads(scan: Plan, listen: Plan) -> list[str]:
    return [tool for tool in missing(scan, listen) if tool not in scan["tools"].get("manual", [])]


def by_hand(scan: Plan, listen: Plan) -> list[str]:
    return [tool for tool in missing(scan, listen) if tool in scan["tools"].get("manual", [])]


def options(scan: Plan) -> list[Plan]:
    return [{"provider": a["id"], "kind": "sign_in"} for a in scan["subscriptions"]["apps"]
            if a["installed"] and not a["signed_in"]]


def make_plan(scan: Plan) -> Plan:
    translate = translate_choice(scan)
    listen = listen_choice(scan, translate)
    tools = downloads(scan, listen)
    size = round(sum(scan["tools"]["sizes"][tool] for tool in tools), 1)
    low = scan["device"]["disk_free_gb"] < size + SPARE_GB
    return {"translate": translate, "listen": listen, "needs": needs(translate, listen),
            "downloads": tools, "download_gb": size, "warnings": ["disk"] if low else [],
            "install_yourself": by_hand(scan, listen), "options": options(scan)}
