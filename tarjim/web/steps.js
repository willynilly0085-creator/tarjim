import { $, api, post } from "./api.js";
import { apply, t } from "./i18n.js";

const KEY_LINKS = {
  gemini: "https://aistudio.google.com/apikey",
  openai: "https://platform.openai.com/api-keys",
  anthropic: "https://console.anthropic.com/settings/keys",
};
const LISTEN = ["gemini", "openai", "local"];
const TRANSLATE = ["gemini", "openai", "anthropic", "claude", "codex", "local"];
const SUBSCRIPTIONS = ["claude", "codex"];

function fact(term, value, bad = false) {
  const dt = document.createElement("dt");
  const dd = document.createElement("dd");
  dt.textContent = term;
  dd.append(Object.assign(document.createElement("bdi"), { textContent: value }));
  dd.classList.toggle("bad", bad);
  return [dt, dd];
}

export async function renderDevice(state) {
  state.system ??= await api("/system");
  const s = state.system;
  const gpu = s.gpu ? `${s.gpu.name} (${s.gpu.memory_gb} GB)` : t("gpuNone");
  $("facts").replaceChildren(...fact(t("gpu"), gpu), ...fact(t("memory"), `${s.memory_gb} GB`),
    ...fact(t("disk"), `${s.disk_free_gb} GB`),
    ...fact(t("ffmpegRow"), t(s.ffmpeg ? "present" : "missing"), !s.ffmpeg));
  $("device-advice").textContent = `${t("recommendCloud")} ${t(s.local_ready ? "localCapable" : "localNot")}`;
}

function fillProviders(select, options, picked) {
  select.replaceChildren(...options.map((p) => new Option(t(`provider_${p}`), p, false, p === picked)));
}

function engineMode(listen, translate) {
  if (SUBSCRIPTIONS.includes(translate)) return "subscription";
  if (listen === translate && ["gemini", "local"].includes(listen)) return listen === "gemini" ? "cloud" : "local";
  return "advanced";
}

function renderSubscriptions(state, translate) {
  const found = state.setup.subscriptions || [];
  fillProviders($("subscription-provider"), found, translate);
  $("subscription-provider").closest(".field").hidden = found.length === 0;
  $("subscription-none").hidden = found.length > 0;
}

export function renderEngine(state) {
  const fresh = !state.setup.listen_provider && !state.setup.translate_provider;
  const { listen, translate } = fresh ? { listen: "gemini", translate: "gemini" } : state.setup.chosen;
  const mode = engineMode(listen, translate);
  document.querySelector(`input[name=engine][value=${mode}]`).checked = true;
  renderSubscriptions(state, translate);
  $("subscription").hidden = mode !== "subscription";
  fillProviders($("listen-provider"), LISTEN, listen);
  fillProviders($("translate-provider"), TRANSLATE, translate);
  $("advanced").hidden = mode !== "advanced";
}

export function engineChoice(state) {
  const mode = document.querySelector("input[name=engine]:checked")?.value || "cloud";
  if (mode === "subscription" && $("subscription-provider").value) {
    return { listen_provider: state.setup.keys.gemini ? "gemini" : "local", translate_provider: $("subscription-provider").value };
  }
  if (mode === "cloud") return { listen_provider: "gemini", translate_provider: "gemini" };
  if (mode === "local") return { listen_provider: "local", translate_provider: "local" };
  return { listen_provider: $("listen-provider").value, translate_provider: $("translate-provider").value };
}

export const neededKeys = (state) =>
  [...new Set([state.setup.chosen.listen, state.setup.chosen.translate])].filter((p) => p in KEY_LINKS);

async function saveKey(provider, form, state) {
  const input = form.querySelector("input");
  const label = form.querySelector(".key-state");
  label.dataset.state = "";
  label.textContent = t("keyChecking");
  try {
    await post("/keys", { provider, key: input.value.trim() });
    state.setup.keys[provider] = true;
    input.value = "";
    label.dataset.state = "ok";
    label.textContent = t("keySaved");
  } catch (error) {
    label.dataset.state = "bad";
    label.textContent = t(error.body?.result === "rejected" ? "keyRejected" : "keyShape");
  }
}

export function renderKeys(state) {
  const needed = neededKeys(state);
  $("keys-none").hidden = needed.length > 0;
  $("key-list").replaceChildren(...needed.map((provider) => {
    const form = $("key-row").content.firstElementChild.cloneNode(true);
    apply(form);
    form.querySelector(".field-label").textContent = t(`key_${provider}`);
    form.querySelector("a").href = KEY_LINKS[provider];
    const label = form.querySelector(".key-state");
    label.dataset.state = state.setup.keys[provider] ? "ok" : "";
    label.textContent = state.setup.keys[provider] ? t("keySaved") : "";
    form.addEventListener("submit", (event) => { event.preventDefault(); saveKey(provider, form, state); });
    return form;
  }));
}

function toolAction(tool, refresh) {
  if (tool.installed) return Object.assign(document.createElement("span"), { className: "ready", textContent: t("installed") });
  if (tool.state === "downloading") return Object.assign(document.createElement("span"), { className: "meta", textContent: t("downloading") });
  const button = Object.assign(document.createElement("button"), {
    type: "button", className: tool.required ? "primary small" : "button-quiet",
    textContent: t(tool.state === "failed" ? "retry" : "download"),
  });
  button.addEventListener("click", () => post(`/tools/${tool.id}`).finally(refresh));
  return button;
}

export async function renderTools(state) {
  state.tools = await api("/tools");
  const refresh = () => renderTools(state);
  $("tool-list").replaceChildren(...state.tools.map((tool) => {
    const row = $("tool-row").content.firstElementChild.cloneNode(true);
    row.querySelector(".tool-name").textContent = `${t(`tool_${tool.id}`)} · ${t(tool.required ? "required" : "optional")}`;
    row.querySelector(".tool-hint").textContent = tool.state === "failed" ? t("failed") : t(`tool_${tool.id}_hint`);
    row.querySelector(".tool-size").textContent = t("sizeGb", { n: tool.size_gb });
    row.querySelector(".tool-action").replaceChildren(toolAction(tool, refresh));
    return row;
  }));
  return state.tools.some((tool) => tool.state === "downloading");
}
