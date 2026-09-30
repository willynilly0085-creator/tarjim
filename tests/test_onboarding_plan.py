"""The setup plan for the people tarjim expects to meet, each on their own kind of computer."""
from typing import Any

from tarjim.onboarding.plan import make_plan

NOTHING_INSTALLED = {"ffmpeg": False, "timing": False, "accuracy": False, "dubbing": False,
                     "local_translation": False}
SIZES = {"ffmpeg": 0.08, "timing": 1.3, "accuracy": 5.9, "dubbing": 1.9, "local_translation": 5.1}


def computer(**given: Any) -> dict[str, Any]:
    g = {"gpu": False, "vram": 0.0, "disk": 200.0, "apps": (), "programs": (), "keys": (),
         "tools": {}, **given}
    return {"device": {"gpu": g["gpu"], "vram_gb": g["vram"], "disk_free_gb": g["disk"],
                       "memory_gb": 16},
            "tools": {"installed": {**NOTHING_INSTALLED, **g["tools"]}, "sizes": SIZES},
            "local": {"programs": list(g["programs"])},
            "subscriptions": {"apps": list(g["apps"])}, "keys": {"saved": list(g["keys"])}}


def app(provider: str, signed_in: bool) -> dict[str, Any]:
    return {"id": provider, "name": provider, "installed": True, "signed_in": signed_in}


def test_a_plain_laptop_is_sent_to_the_free_gemini_key_for_both_listening_and_translation() -> None:
    plan = make_plan(computer())
    assert plan["translate"]["provider"] == "gemini" and plan["listen"]["provider"] == "gemini"
    assert plan["needs"] == [{"kind": "key", "provider": "gemini"}]
    assert plan["downloads"] == ["ffmpeg", "timing"] and plan["download_gb"] == 1.4


def test_a_gaming_pc_that_needs_the_gemini_key_anyway_hears_with_it_too() -> None:
    plan = make_plan(computer(gpu=True, vram=12))
    assert plan["listen"] == {"provider": "gemini", "reason": "same_key", "ready": False}
    assert plan["downloads"] == ["ffmpeg", "timing"]


def test_a_subscriber_with_a_graphics_card_listens_on_the_card() -> None:
    plan = make_plan(computer(gpu=True, vram=12, apps=[app("claude", True)]))
    assert plan["listen"] == {"provider": "local", "reason": "gpu", "ready": False}
    assert plan["downloads"] == ["ffmpeg", "timing", "accuracy"]


def test_a_signed_in_claude_subscription_translates_without_any_key() -> None:
    plan = make_plan(computer(gpu=True, vram=16, apps=[app("claude", True)]))
    assert plan["translate"]["provider"] == "claude" and plan["translate"]["reason"] == "signed_in"
    assert plan["needs"] == []


def test_a_subscription_without_a_graphics_card_still_needs_a_way_to_hear() -> None:
    plan = make_plan(computer(apps=[app("codex", True)]))
    assert plan["translate"]["provider"] == "codex"
    assert plan["listen"]["provider"] == "gemini" and plan["listen"]["reason"] == "no_gpu"
    assert plan["needs"] == [{"kind": "key", "provider": "gemini"}]


def test_an_installed_ollama_with_a_model_is_used_and_started() -> None:
    ollama = {"id": "ollama", "name": "Ollama", "running": False, "can_start": True,
              "models": ["gpt-oss:120b", "aya-expanse:8b", "qwen2.5:14b"]}
    plan = make_plan(computer(gpu=True, vram=16, programs=[ollama]))
    assert plan["translate"] == {"provider": "local", "server": "ollama", "model": "aya-expanse:8b",
                                 "reason": "local", "ready": False}
    assert {"kind": "start_local", "server": "ollama"} in plan["needs"]


def test_a_saved_gemini_key_needs_nothing_more_than_the_timing_tools() -> None:
    plan = make_plan(computer(keys=["gemini"], tools={"ffmpeg": True}))
    assert plan["translate"]["provider"] == "gemini" and plan["listen"]["provider"] == "gemini"
    assert plan["needs"] == [] and plan["downloads"] == ["timing"]


def test_a_nearly_full_disk_is_warned_about_before_downloading() -> None:
    assert "disk" in make_plan(computer(disk=3))["warnings"]


def test_an_installed_but_signed_out_subscription_is_offered_not_chosen() -> None:
    plan = make_plan(computer(apps=[app("claude", False)]))
    assert plan["translate"]["provider"] == "gemini"
    assert {"provider": "claude", "kind": "sign_in"} in plan["options"]


def test_on_a_mac_ffmpeg_is_listed_to_install_by_hand_instead_of_downloaded() -> None:
    scan = computer()
    scan["tools"]["manual"] = ["ffmpeg"]
    plan = make_plan(scan)
    assert plan["downloads"] == ["timing"] and plan["download_gb"] == 1.3
    assert plan["install_yourself"] == ["ffmpeg"]
