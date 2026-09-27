import { $, show } from "./dom.js";
import { keyStatus, saveKey } from "./keys.js";
import { askToPair, claimPending, serverBase } from "./pairing.js";
import { api, remember, settings, t } from "./shared.js";

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
export async function openSettings() {
  const saved = await settings();
  $("server").value = saved.server;
  $("settings-token").value = saved.token;
  const keys = await keyStatus().catch(() => ({}));
  $("settings-gemini").placeholder = keys.gemini ? t("keySet") : "";
  $("settings-fish").placeholder = keys.fish ? t("keySet") : "";
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
  $("settings-notice").textContent = problems[0] || t("saved");
}

export function wirePanels({ ready, back, leave }) {
  $("pair-form").addEventListener("submit", (event) => pair(event, ready));
  $("pair-auto").addEventListener("click", () => autoPair(ready));
  $("open-tarjim").addEventListener("click", async () => chrome.tabs.create({ url: `${await serverBase()}/` }));
  $("key-form").addEventListener("submit", (event) => submitKey(event, ready));
  $("settings-form").addEventListener("submit", saveSettings);
  $("retry-connect").addEventListener("click", back);
  $("close-settings").addEventListener("click", back);
  $("open-settings").addEventListener("click", () => { leave(); openSettings(); });
}
