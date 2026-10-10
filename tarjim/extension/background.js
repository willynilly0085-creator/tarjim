import { buildMenus, isMode, OTHER } from "./menus.js";
import { claimPending, sendWaitingJob } from "./pairing.js";
import { clickedPost, downloadable } from "./posts.js";
import { ApiError, api, errorLabel, loadWords, post, remember, settings, t } from "./shared.js";

const POLL = "poll";

self.addEventListener("unhandledrejection", (event) => {
  if (event.reason instanceof ApiError) event.preventDefault();
});

async function start() {
  await loadWords();
  buildMenus();
  chrome.alarms.create(POLL, { periodInMinutes: 0.5 });
}

chrome.runtime.onInstalled.addListener(start);
chrome.runtime.onStartup.addListener(start);
chrome.storage.onChanged.addListener((changes) => { if (changes.target || changes.mode) buildMenus(); });

async function pickUrl(info, tab) {
  const direct = [info.linkUrl, info.srcUrl].find(downloadable);
  return direct || [await clickedPost(info, tab), info.pageUrl, tab?.url].find(downloadable) || "";
}

function notify(id, title, message) {
  chrome.notifications.create(id, { type: "basic", iconUrl: "icons/128.png", title, message });
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  await loadWords();
  if (info.menuItemId === OTHER) {
    chrome.tabs.create({ url: chrome.runtime.getURL("app.html?page=1") });
    return;
  }
  if (!isMode(info.menuItemId)) return;
  const url = await pickUrl(info, tab);
  if (!url) {
    notify(`nourl-${Date.now()}`, t("appName"), t("menuNoVideo"));
    return;
  }
  const { target, dialect } = await settings();
  const mode = info.menuItemId;
  try {
    await post("/jobs", { url, target, dialect, mode });
    await remember(mode.startsWith("dub-") ? { mode, voice: mode.slice(4) } : { mode });
    refresh();
    await chrome.action.openPopup().catch(() => notify(`start-${Date.now()}`, t("appName"), t("notifyStarted")));
  } catch (error) {
    const unpaired = error.kind !== "offline";
    if (unpaired) await remember({ waitingJob: { url, target, dialect, mode } });
    chrome.tabs.create({ url: chrome.runtime.getURL(unpaired ? "app.html?pair=auto" : "app.html") });
  }
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== POLL) return;
  if (await loadWords()) buildMenus();
  await matchEngine();
  if ((await claimPending()) === "paired") {
    notify(`paired-${Date.now()}`, t("appName"), t("pairedNotice"));
    await sendWaitingJob();
  }
  refresh();
});

// After the engine updates itself it refreshes this extension's folder; reload once to match it.
async function matchEngine() {
  const engine = (await api("/update").catch(() => null))?.extension;
  const { reloadedFor } = await chrome.storage.local.get("reloadedFor");
  if (!engine || engine === chrome.runtime.getManifest().version || engine === reloadedFor) return;
  await chrome.storage.local.set({ reloadedFor: engine });
  chrome.runtime.reload();
}

async function refresh() {
  let jobs;
  try {
    jobs = await api("/jobs");
  } catch {
    chrome.action.setBadgeText({ text: "" });
    return;
  }
  const active = jobs.filter((job) => !job.finished).length;
  chrome.action.setBadgeBackgroundColor({ color: "#e8c547" });
  chrome.action.setBadgeText({ text: active ? String(active) : "" });
  await announce(jobs);
}

async function announce(jobs) {
  const { seen = {} } = await chrome.storage.session.get("seen");
  for (const job of jobs.filter((j) => j.finished && seen[j.id] === false)) {
    const done = job.stage === "done";
    notify(job.id, done ? t("notifyDone") : t("notifyFailed"), done ? job.title : errorLabel(job));
  }
  const next = Object.fromEntries(jobs.map((job) => [job.id, job.finished]));
  await chrome.storage.session.set({ seen: next });
}
