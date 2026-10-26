import { $, show } from "./dom.js";
import { keyStatus, saveKey } from "./keys.js";
import { askToPair, claimPending, openPage, sendWaitingJob } from "./pairing.js";
import { ApiError, api, remember, settings, t } from "./shared.js";

window.addEventListener("unhandledrejection", (event) => {
  if (!(event.reason instanceof ApiError)) return;
  event.preventDefault();
  if (event.reason.kind === "token") showPair();
  else show("offline");
});

async function pair(event, ready) {
  event.preventDefault();
  await remember({ token: $("token").value.trim() });
  try {
    await api("/jobs");
    $("pair-error").hidden = true;
    await ready();
  } catch (error) {
    $("pair-error").textContent = t(error.kind === "offline" ? "actionOffline" : "pairWrong");
    $("pair-error").hidden = false;
  }
}

function showCode(code) {
  $("pair-waiting").hidden = false;
  $("pair-waiting").textContent = `${t("pairWaiting")} \u2066${code}\u2069`;
}

// The code stays on the pairing screen until the request is answered, even after the popup closed.
export async function showPair() {
  show("pair");
  const { pairId, pairCode } = await chrome.storage.local.get(["pairId", "pairCode"]);
  if (pairId && pairCode) showCode(pairCode);
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const ATTEMPTS = 400;
const ENDED = { denied: "pairDenied", none: "pairExpired" };
const CODE_NOTICE = "pair-code";
let pageTab = null;

// The code is typed on tarjim's page, and going there closes this popup: so the page opens behind
// it, and the code also stays in a notification until the request is answered.
function noticeCode(code) {
  chrome.notifications.create(CODE_NOTICE, { type: "basic", iconUrl: "icons/128.png", title: t("appName"),
    message: `${t("pairWaiting")} ${code}`, requireInteraction: true });
}

async function showPage() {
  const shown = pageTab && await chrome.tabs.update(pageTab.id, { active: true }).catch(() => null);
  if (!shown) await openPage();
}

async function answer(code) {
  for (let i = 0; i < ATTEMPTS; i += 1) {
    await wait(1500);
    const result = await claimPending();
    if (result === "unreachable") $("pair-waiting").textContent = t("pairUnreachable");
    else if (result === "waiting") showCode(code);
    else return result;
  }
  return "none";
}

export async function autoPair(ready) {
  show("pair");
  const asked = await askToPair();
  if (!asked?.id) return show("offline");
  showCode(asked.code);
  noticeCode(asked.code);
  $("open-tarjim").hidden = false;
  pageTab = await openPage("", false);
  const result = await answer(asked.code);
  chrome.notifications.clear(CODE_NOTICE);
  if (result !== "paired") return void ($("pair-waiting").textContent = t(ENDED[result] || "pairExpired"));
  await sendWaitingJob();
  return ready();
}

async function fillSummary() {
  const box = $("connection-summary");
  box.textContent = t("loading");
  const [now, phone] = await Promise.all([api("/connections/current").catch(() => null),
    api("/phone").catch(() => null)]);
  if (!now) return void (box.textContent = t("summaryFailed"));
  const row = (label, value) => [Object.assign(document.createElement("dt"), { textContent: label }),
    Object.assign(document.createElement("dd"), { textContent: value })];
  box.replaceChildren(...row(t("summaryTranslate"), now.model ? `${now.name} · ${now.model}` : now.name),
    ...row(t("summaryListen"), now.listen === "local" ? t("onDevice") : now.listen_name),
    ...(phone ? row(t("summaryPhone"), phone.paired ? `${t("phoneLinked")} \u2066@${phone.bot}\u2069` : t("phoneNotLinked")) : []));
  $("open-phone").textContent = t(phone?.paired ? "phoneSettingsButton" : "phoneLinkButton");
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

const openSetup = () => openPage("#setup");

async function saveSettings(event) {
  event.preventDefault();
  await remember({ server: $("server").value.trim(), token: $("settings-token").value.trim() });
  const typed = $("settings-fish").value.trim();
  $("settings-notice").textContent = typed ? t("keyChecking") : "";
  const problem = await saveKey("fish", typed).catch(() => t("keyFailed"));
  $("settings-notice").textContent = problem || t("saved");
  if (typed && !problem) {
    $("settings-fish").value = "";
    $("settings-fish").placeholder = t("keySet");
  }
}

// "Try again" and "I finished" say so when nothing changed, instead of showing the same screen.
function againOn(view, note, words, back) {
  return async () => {
    $(note).textContent = t("loading");
    await back();
    $(note).textContent = $(`view-${view}`).hidden ? "" : t(words);
  };
}

export function wirePanels({ ready, back, leave }) {
  $("pair-form").addEventListener("submit", (event) => pair(event, ready));
  $("pair-auto").addEventListener("click", () => autoPair(ready));
  $("open-tarjim").addEventListener("click", showPage);
  $("open-setup").addEventListener("click", openSetup);
  $("open-keys-settings").addEventListener("click", () => openPage("#connect"));
  $("open-phone").addEventListener("click", () => openPage("#phone"));
  $("open-full-setup").addEventListener("click", openSetup);
  $("setup-done").addEventListener("click", againOn("setup", "setup-note", "setupNotDone", back));
  $("settings-form").addEventListener("submit", saveSettings);
  $("retry-connect").addEventListener("click", againOn("offline", "offline-note", "stillOffline", back));
  $("close-settings").addEventListener("click", back);
  $("open-settings").addEventListener("click", () => { leave(); openSettings(); });
}
