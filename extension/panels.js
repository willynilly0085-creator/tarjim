import { $, show } from "./dom.js";
import { keyStatus, saveKey } from "./keys.js";
import { askToPair, claimPending, serverBase } from "./pairing.js";
import { api, post, remember, settings, t } from "./shared.js";

async function pair(event, ready) {
  event.preventDefault();
  await remember({ token: $("token").value.trim() });
  try {
    await api("/jobs");
    $("pair-error").hidden = true;
    await ready();
  } catch {
    $("pair-error").hidden = false;
  }
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const ATTEMPTS = 400;

async function autoPair(ready) {
  const id = await askToPair();
  if (!id) return show("offline");
  $("pair-waiting").hidden = false;
  $("pair-waiting").textContent = t("pairWaiting");
  $("open-tarjim").hidden = false;
  chrome.tabs.create({ url: `${await serverBase()}/` });
  for (let i = 0; i < ATTEMPTS; i += 1) {
    await wait(1500);
    const result = await claimPending();
    if (result === "paired") return ready();
    if (result !== "waiting") break;
  }
  $("pair-waiting").textContent = t("pairDenied");
}
let engineAtOpen = "";

function syncEngine() {
  $("local-model-field").hidden = $("settings-engine").value !== "local";
}

async function fillEngine() {
  const setup = await api("/setup").catch(() => null);
  if (!setup) return;
  const { listen, translate } = setup.chosen;
  const engine = listen === "local" && translate === "local" ? "local"
    : listen === "gemini" && translate === "gemini" ? "cloud" : "advanced";
  $("settings-engine").value = engine;
  engineAtOpen = engine;
  const { models = [], chosen = "" } = await api("/local-models").catch(() => ({}));
  $("settings-local-model").replaceChildren(...models.map((m) => new Option(m, m, false, m === chosen)));
  $("local-model-hint").textContent = t(models.length ? "localModelHint" : "localModelNone");
  syncEngine();
}

async function saveEngine() {
  const engine = $("settings-engine").value;
  if (engine === "advanced") {
    if (engineAtOpen !== "advanced") chrome.tabs.create({ url: `${await serverBase()}/` });
    return;
  }
  const provider = engine === "local" ? "local" : "gemini";
  const model = $("settings-local-model").value;
  const extra = engine === "local" && model ? { local_model: model } : {};
  await post("/setup", { listen_provider: provider, translate_provider: provider, ...extra });
  engineAtOpen = engine;
}

export async function openSettings() {
  const saved = await settings();
  $("server").value = saved.server;
  $("settings-token").value = saved.token;
  const keys = await keyStatus().catch(() => ({}));
  $("settings-gemini").placeholder = keys.gemini ? t("keySet") : "";
  $("settings-fish").placeholder = keys.fish ? t("keySet") : "";
  await fillEngine();
  show("settings");
}

async function submitKey(event, ready) {
  event.preventDefault();
  const button = event.submitter;
  button.disabled = true;
  button.textContent = t("keyChecking");
  const problem = await saveKey("gemini", $("gemini-key").value);
  button.disabled = false;
  button.textContent = t("keySave");
  $("key-error").hidden = !problem;
  $("key-error").textContent = problem;
  if (!problem && $("gemini-key").value.trim()) await ready();
}

async function saveSettings(event) {
  event.preventDefault();
  await remember({ server: $("server").value.trim(), token: $("settings-token").value.trim() });
  $("settings-notice").textContent = t("keyChecking");
  const problems = [await saveKey("gemini", $("settings-gemini").value),
    await saveKey("fish", $("settings-fish").value)].filter(Boolean);
  await saveEngine().catch(() => problems.push(t("errUnknown")));
  $("settings-notice").textContent = problems[0] || t("saved");
}

export function wirePanels({ ready, back, leave }) {
  $("pair-form").addEventListener("submit", (event) => pair(event, ready));
  $("pair-auto").addEventListener("click", () => autoPair(ready));
  $("open-tarjim").addEventListener("click", async () => chrome.tabs.create({ url: `${await serverBase()}/` }));
  $("key-form").addEventListener("submit", (event) => submitKey(event, ready));
  $("settings-form").addEventListener("submit", saveSettings);
  $("settings-engine").addEventListener("change", syncEngine);
  $("retry-connect").addEventListener("click", back);
  $("close-settings").addEventListener("click", back);
  $("open-settings").addEventListener("click", () => { leave(); openSettings(); });
}
