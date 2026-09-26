import { api, errorLabel, mediaUrl, post, settings, t } from "./shared.js";

const MENU_ROOT = "tarjim";
const MENU_MODES = { "tarjim-burn": "burn", "tarjim-srt": "srt", "tarjim-dub": "dub-clone" };
const POLL = "poll";
const CONTEXTS = ["link", "video", "audio", "page"];

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({ id: MENU_ROOT, title: t("menuRoot"), contexts: CONTEXTS });
    chrome.contextMenus.create({ id: "tarjim-burn", parentId: MENU_ROOT, title: t("menuBurn"), contexts: CONTEXTS });
    chrome.contextMenus.create({ id: "tarjim-srt", parentId: MENU_ROOT, title: t("menuSrt"), contexts: CONTEXTS });
    chrome.contextMenus.create({ id: "tarjim-dub", parentId: MENU_ROOT, title: t("menuDub"), contexts: CONTEXTS });
  });
  chrome.alarms.create(POLL, { periodInMinutes: 0.5 });
});

chrome.runtime.onStartup.addListener(() => chrome.alarms.create(POLL, { periodInMinutes: 0.5 }));

function pickUrl(info, tab) {
  const candidates = [info.linkUrl, info.srcUrl, info.pageUrl, tab?.url];
  return candidates.find(mediaUrl);
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const mode = MENU_MODES[info.menuItemId];
  const url = pickUrl(info, tab);
  if (!mode || !url) return;
  const { target, dialect } = await settings();
  try {
    await post("/jobs", { url, target, dialect, mode });
    chrome.action.setBadgeText({ text: "…" });
    refresh();
  } catch (error) {
    const body = error.kind === "offline" ? t("offlineTitle") : t("pairTitle");
    notify(`fail-${Date.now()}`, t("notifyFailed"), body);
  }
});

chrome.alarms.onAlarm.addListener((alarm) => alarm.name === POLL && refresh());

function notify(id, title, message) {
  chrome.notifications.create(id, { type: "basic", iconUrl: "icons/128.png", title, message });
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
