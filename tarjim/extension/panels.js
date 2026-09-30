import { $, show } from "./dom.js";
import { keyStatus, saveKey } from "./keys.js";
import { askToPair, claimPending, sendWaitingJob, serverBase } from "./pairing.js";
import { ApiError, api, remember, settings, t } from "./shared.js";

window.addEventListener("unhandledrejection", (event) => {
  if (!(event.reason instanceof ApiError)) return;
  event.preventDefault();
  show(event.reason.kind === "token" ? "pair" : "offline");
});

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

export async function autoPair(ready) {
  show("pair");
  const id = await askToPair();
  if (!id) return show("offline");
  $("pair-waiting").hidden = false;
  $("pair-waiting").textContent = t("pairWaiting");
  $("open-tarjim").hidden = false;
  chrome.tabs.create({ url: `${await serverBase()}/` });
  for (let i = 0; i < ATTEMPTS; i += 1) {
    await wait(1500);
    const result = await claimPending();
    if (result === "paired") {
      await sendWaitingJob();
      return ready();
    }
    if (result !== "waiting") break;
  }
  $("pair-waiting").textContent = t("pairDenied");
}
async function fillSummary() {
  const box = $("connection-summary");
  box.textContent = t("loading");
  const now = await api("/connections/current").catch(() => null);
  if (!now) return;
  const row = (label, value) => [Object.assign(document.createElement("dt"), { textContent: label }),
    Object.assign(document.createElement("dd"), { textContent: value })];
  box.replaceChildren(...row(t("summaryTranslate"), now.model ? `${now.name} · ${now.model}` : now.name),
    ...row(t("summaryListen"), now.listen === "local" ? t("onDevice") : now.listen_name));
}

export async function openSettings() {
  const saved = await settings();
  $("server").value = saved.server;
  $("settings-token").value = saved.token;
  const keys = await keyStatus().catch(() => ({}));
  $("settings-fish").placeholder = keys.fish ? t("keySet") : "";
  show("settings");
  await fillSummary();
}

async function openSetup() {
  chrome.tabs.create({ url: `${await serverBase()}/#setup` });
}

async function saveSettings(event) {
  event.preventDefault();
  await remember({ server: $("server").value.trim(), token: $("settings-token").value.trim() });
  $("settings-notice").textContent = t("keyChecking");
  const problem = await saveKey("fish", $("settings-fish").value);
  $("settings-notice").textContent = problem || t("saved");
}

export function wirePanels({ ready, back, leave }) {
  $("pair-form").addEventListener("submit", (event) => pair(event, ready));
  $("pair-auto").addEventListener("click", () => autoPair(ready));
  $("open-tarjim").addEventListener("click", async () => chrome.tabs.create({ url: `${await serverBase()}/` }));
  $("open-setup").addEventListener("click", openSetup);
  $("open-full-setup").addEventListener("click", openSetup);
  $("setup-done").addEventListener("click", back);
  $("settings-form").addEventListener("submit", saveSettings);
  $("retry-connect").addEventListener("click", back);
  $("close-settings").addEventListener("click", back);
  $("open-settings").addEventListener("click", () => { leave(); openSettings(); });
}
