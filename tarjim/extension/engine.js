import { $ } from "./dom.js";
import { serverBase } from "./pairing.js";
import { api, post, t } from "./shared.js";

const SUBSCRIPTIONS = { claude: "providerClaude", codex: "providerCodex", copilot: "providerCopilot", antigravity: "providerAntigravity" };
let atOpen = "";
let geminiKey = false;

function modeOf(listen, translate) {
  if (translate in SUBSCRIPTIONS) return "subscription";
  if (listen === translate && (listen === "local" || listen === "gemini")) return listen === "local" ? "local" : "cloud";
  return "advanced";
}

export function syncEngine() {
  const mode = $("settings-engine").value;
  $("local-model-field").hidden = mode !== "local";
  $("subscription-field").hidden = mode !== "subscription";
}

function fillSubscriptions(found, picked) {
  $("settings-subscription").replaceChildren(...found.map((p) => new Option(t(SUBSCRIPTIONS[p]), p, false, p === picked)));
  $("settings-subscription").hidden = found.length === 0;
  $("subscription-none").hidden = found.length > 0;
}

export async function fillEngine() {
  const setup = await api("/setup").catch(() => null);
  if (!setup) return;
  const { listen, translate } = setup.chosen;
  geminiKey = Boolean(setup.keys?.gemini);
  atOpen = modeOf(listen, translate);
  $("settings-engine").value = atOpen;
  fillSubscriptions(setup.subscriptions || [], translate);
  const { models = [], chosen = "" } = await api("/local-models").catch(() => ({}));
  $("settings-local-model").replaceChildren(...models.map((m) => new Option(m, m, false, m === chosen)));
  $("local-model-hint").textContent = t(models.length ? "localModelHint" : "localModelNone");
  syncEngine();
}

function choiceFor(mode) {
  if (mode === "subscription") {
    const picked = $("settings-subscription").value;
    return picked ? { listen_provider: geminiKey ? "gemini" : "local", translate_provider: picked } : null;
  }
  const provider = mode === "local" ? "local" : "gemini";
  const model = $("settings-local-model").value;
  return { listen_provider: provider, translate_provider: provider, ...(mode === "local" && model ? { local_model: model } : {}) };
}

export async function saveEngine() {
  const mode = $("settings-engine").value;
  if (mode === "advanced") {
    if (atOpen !== "advanced") chrome.tabs.create({ url: `${await serverBase()}/` });
    return;
  }
  const choice = choiceFor(mode);
  if (!choice) return;
  await post("/setup", choice);
  atOpen = mode;
}
