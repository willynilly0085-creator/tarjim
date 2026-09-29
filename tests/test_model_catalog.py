"""Every provider's models, named like its own app, newest first, the lightest suggested."""
from tarjim.engines.model_catalog import describe, pretty


def names(models: list[dict[str, str]], group: str) -> list[str]:
    return [m["name"] for m in models if m["group"] == group]


def test_gemini_keeps_its_own_names_drops_non_text_models_and_suggests_flash() -> None:
    rows = [("gemini-3.8-pro", "Gemini 3.8 Pro", ""), ("gemini-3.8-flash", "Gemini 3.8 Flash", ""),
            ("gemini-3.7-flash", "Gemini 3.7 Flash", ""), ("gemini-3.8-flash-tts", "TTS", ""),
            ("text-embedding-004", "Embedding", ""), ("imagen-5", "Imagen", "")]
    models = describe(rows)
    assert names(models, "latest") == ["Gemini 3.8 Pro", "Gemini 3.8 Flash"]
    assert names(models, "more") == ["Gemini 3.7 Flash"]
    assert [m["id"] for m in models if m["suggested"]] == ["gemini-3.8-flash"]


def test_ids_without_names_become_readable() -> None:
    assert pretty("deepseek-chat") == "DeepSeek Chat"
    assert pretty("gpt-5.6-mini") == "GPT 5.6 Mini"
    assert pretty("deepseek-v4-flash-free") == "DeepSeek V4 Flash Free"
    assert pretty("grok-5-mini") == "Grok 5 Mini"


def test_deepseek_suggests_its_chat_model() -> None:
    models = describe([("deepseek-reasoner", "", ""), ("deepseek-chat", "", "")])
    assert [m["name"] for m in models if m["suggested"]] == ["DeepSeek Chat"]


def test_a_subscription_list_keeps_the_apps_own_order_and_hides_hidden_models() -> None:
    rows = [("gpt-6-luna", "GPT-6-Luna", "Fast and affordable model for easier tasks."),
            ("gpt-5.6-terra", "GPT-5.6-Terra", "Older balanced model for straightforward work."),
            ("gpt-5.5", "GPT-5.5", "Legacy coding model.")]
    models = describe(rows, keep_order=True)
    assert [m["name"] for m in models] == ["GPT-6-Luna", "GPT-5.6-Terra", "GPT-5.5"]
    assert [m["id"] for m in models if m["suggested"]] == ["gpt-6-luna"]
    assert names(models, "more") == ["GPT-5.6-Terra", "GPT-5.5"]


def test_version_numbers_split_by_dashes_read_as_one_version() -> None:
    assert pretty("claude-opus-5-5") == "Claude Opus 5.5"


def test_a_free_light_model_is_suggested_over_a_paid_one() -> None:
    models = describe([("gpt-6-luna", "", ""), ("deepseek-v4-flash-free", "", ""),
                       ("claude-opus-5-5", "", "")])
    assert [m["id"] for m in models if m["suggested"]] == ["deepseek-v4-flash-free"]
