import { t } from "./i18n.js";

const NAMES = { gemini: "Google Gemini", openai: "OpenAI", anthropic: "Anthropic Claude", openrouter: "OpenRouter",
  deepseek: "DeepSeek", qwen: "Qwen", mistral: "Mistral", groq: "Groq", xai: "xAI Grok", opencode: "OpenCode Zen", opencode_go: "OpenCode Go", kimi: "Kimi", glm: "GLM", minimax: "MiniMax",
  custom: "OpenAI-compatible" };
const PREFERENCE = ["aya", "qwen", "gemma", "llama", "mistral"];
const TOO_BIG = /[:-](\d{2,3})b\b/;

function bestModel(models) {
  const fitting = models.filter((m) => !(TOO_BIG.test(m) && Number(m.match(TOO_BIG)[1]) >= 30));
  return PREFERENCE.map((family) => fitting.find((m) => m.toLowerCase().includes(family))).find(Boolean) || fitting[0] || "";
}

function option(value, label, why, choice, disabled = false) {
  return { value, label, why, disabled, choice: { ...choice, value },
    matches: (c) => c.provider === choice.provider && (c.server || "") === (choice.server || "") };
}

function subscriptions(scan) {
  return scan.subscriptions.apps.filter((a) => a.installed).map((a) => option(`sub:${a.id}`,
    a.signed_in ? a.name : `${a.name} · ${t("needsSignIn")}`, t(a.signed_in ? "reason_signed_in" : "reason_sign_in_first"),
    { provider: a.id, ready: a.signed_in }));
}

function locals(scan) {
  return scan.local.programs.filter((p) => p.models.length && (p.running || p.can_start)).map((p) => {
    const model = bestModel(p.models);
    return option(`local:${p.id}`, `${p.name} · ${model}`, t(scan.device.gpu ? "reason_local" : "reason_local_slow"),
      { provider: "local", server: p.id, model, ready: p.running });
  });
}

export function translateOptions(scan) {
  const keys = scan.keys.saved.map((id) => option(`key:${id}`, NAMES[id] || id, t("reason_key"), { provider: id, ready: true }));
  const free = scan.keys.saved.includes("gemini") ? []
    : [option("key:gemini", `Google Gemini · ${t("freeKey")}`, t("reason_free_key"), { provider: "gemini", ready: false })];
  const other = option("other", t("otherProvider"), t("reason_other"), { provider: "other", ready: false });
  return [...subscriptions(scan), ...keys, ...locals(scan), ...free, other];
}

export function listenOptions(scan) {
  const saved = scan.keys.saved;
  const accuracy = scan.tools.installed.accuracy;
  const local = option("local", accuracy ? t("listenLocalName") : `${t("listenLocalName")} · ${t("needsDownload", { gb: scan.tools.sizes.accuracy })}`,
    t(scan.device.gpu ? "reason_gpu" : "reason_cpu_slow"), { provider: "local", ready: accuracy });
  const gemini = option("gemini", saved.includes("gemini") ? "Google Gemini" : `Google Gemini · ${t("freeKey")}`,
    t("reason_gemini_listen"), { provider: "gemini", ready: saved.includes("gemini") });
  const openai = saved.includes("openai") ? [option("openai", "OpenAI", t("reason_key"), { provider: "openai", ready: true })] : [];
  const cloudFirst = !scan.device.gpu;
  return cloudFirst ? [gemini, local, ...openai] : [local, gemini, ...openai];
}
