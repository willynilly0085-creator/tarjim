"""Every way to connect an AI: an API key, a subscription the person already pays for, or a
model running on this computer."""
from dataclasses import dataclass

API = "api"
SUBSCRIPTION = "subscription"
LOCAL = "local"


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    method: str
    hears: bool = False
    base_url: str = ""
    key_url: str = ""
    program: str = ""
    login: tuple[str, ...] = ()
    install: str = ""
    models: tuple[str, ...] = ()
    plan: bool = False

    @property
    def key_name(self) -> str:
        return f"{self.id}_api_key" if self.method == API else ""

    @property
    def model_name(self) -> str:
        return f"{self.id}_model"


PROVIDERS = (
    Provider("gemini", "Google Gemini", API, hears=True,
             key_url="https://aistudio.google.com/apikey"),
    Provider("openai", "OpenAI", API, hears=True, base_url="https://api.openai.com/v1",
             key_url="https://platform.openai.com/api-keys"),
    Provider("anthropic", "Anthropic Claude", API,
             key_url="https://console.anthropic.com/settings/keys"),
    Provider("openrouter", "OpenRouter", API, base_url="https://openrouter.ai/api/v1",
             key_url="https://openrouter.ai/settings/keys"),
    Provider("deepseek", "DeepSeek", API, base_url="https://api.deepseek.com/v1",
             key_url="https://platform.deepseek.com/api_keys"),
    Provider("qwen", "Qwen (Alibaba Cloud)", API,
             base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
             key_url="https://modelstudio.console.alibabacloud.com/"),
    Provider("mistral", "Mistral", API, base_url="https://api.mistral.ai/v1",
             key_url="https://console.mistral.ai/api-keys"),
    Provider("groq", "Groq", API, base_url="https://api.groq.com/openai/v1",
             key_url="https://console.groq.com/keys"),
    Provider("xai", "xAI Grok", API, base_url="https://api.x.ai/v1",
             key_url="https://console.x.ai/"),
    Provider("opencode", "OpenCode Zen", API, base_url="https://opencode.ai/zen/v1",
             key_url="https://opencode.ai/auth"),
    Provider("kimi", "Kimi (Moonshot)", API, base_url="https://api.moonshot.ai/v1",
             key_url="https://platform.kimi.ai/console/api-keys"),
    Provider("glm", "GLM (Z.ai)", API, base_url="https://api.z.ai/api/paas/v4",
             key_url="https://z.ai/manage-apikey/apikey-list"),
    Provider("minimax", "MiniMax", API, base_url="https://api.minimax.io/v1",
             key_url="https://platform.minimax.io"),
    Provider("opencode_go", "OpenCode Go", API, base_url="https://opencode.ai/zen/go/v1",
             key_url="https://opencode.ai/auth", plan=True),
    Provider("custom", "OpenAI-compatible", API),
    Provider("claude", "Claude", SUBSCRIPTION, program="claude", login=("claude",),
             install="npm install -g @anthropic-ai/claude-code",
             models=("opus", "sonnet", "haiku")),
    Provider("codex", "ChatGPT", SUBSCRIPTION, program="codex", login=("codex", "login"),
             install="npm install -g @openai/codex"),
    Provider("copilot", "GitHub Copilot", SUBSCRIPTION, program="copilot", login=("copilot",),
             install="npm install -g @github/copilot",
             models=("gpt-5.4", "claude-haiku-4.5", "gpt-5.3-codex")),
    Provider("antigravity", "Google AI (Antigravity)", SUBSCRIPTION, program="agy", login=("agy",),
             install="https://antigravity.google/docs/cli"),
)
BY_ID = {provider.id: provider for provider in PROVIDERS}


def of_method(method: str) -> list[Provider]:
    return [provider for provider in PROVIDERS if provider.method == method]


def compatible(provider: Provider) -> bool:
    return provider.method == API and provider.id not in ("gemini", "anthropic")
