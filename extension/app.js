import { watchJobs } from "./jobs.js";
import { api, mediaUrl, post, remember, settings, t } from "./shared.js";
import { isMedia, upload } from "./upload.js";

const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const pageMode = params.get("page") === "1";
const state = { url: "", file: null, languages: new Map(), poll: 0 };

function applyText() {
  document.documentElement.lang = chrome.i18n.getUILanguage();
  document.documentElement.dir = chrome.i18n.getMessage("@@bidi_dir") || "ltr";
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-label]").forEach((el) => {
    el.setAttribute("aria-label", t(el.dataset.i18nLabel));
    el.title = t(el.dataset.i18nLabel);
  });
  document.body.classList.toggle("page", pageMode);
}

function show(view) {
  document.querySelectorAll(".view").forEach((el) => { el.hidden = el.id !== `view-${view}`; });
}

function linkState(online) {
  $("link-state").dataset.state = online ? "online" : "offline";
  $("link-text").textContent = t(online ? "statusOnline" : "statusOffline");
}

async function connect() {
  clearInterval(state.poll);
  try {
    await api("/ping");
  } catch {
    linkState(false);
    return show("offline");
  }
  linkState(true);
  try {
    await api("/jobs");
  } catch (error) {
    return show(error.kind === "token" ? "pair" : "offline");
  }
  await openMain();
}

async function loadLanguages(target) {
  const select = $("target");
  const languages = await api("/languages");
  state.languages = new Map(languages.map((l) => [l.code, l.native]));
  select.replaceChildren(...languages.map((l) => new Option(l.native, l.code, false, l.code === target)));
}

function syncDialect() {
  $("dialect-field").hidden = $("target").value !== "ar";
}

async function describeSource() {
  if (pageMode) {
    $("source-tab").hidden = true;
    $("drop").hidden = false;
    $("open-file-page").hidden = true;
    return;
  }
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const usable = mediaUrl(tab?.url);
  state.url = usable ? tab.url : "";
  $("source-tab").hidden = !usable;
  $("source-none").hidden = usable;
  $("tab-title").textContent = tab?.title || "";
  $("tab-host").textContent = usable ? new URL(tab.url).hostname.replace(/^www\./, "") : "";
}

async function openMain() {
  show("main");
  const saved = await settings();
  await loadLanguages(saved.target);
  document.querySelector(`input[name=dialect][value=${saved.dialect}]`).checked = true;
  document.querySelector(`input[name=mode][value=${saved.mode}]`).checked = true;
  syncDialect();
  await describeSource();
  refreshButton();
  state.poll = watchJobs(state.languages);
}

function choices() {
  const form = $("order");
  return { target: $("target").value, dialect: form.dialect.value, mode: form.mode.value };
}

function sourceReady() {
  return pageMode ? Boolean(state.file) || mediaUrl($("link").value.trim()) : Boolean(state.url);
}

function refreshButton() {
  $("go").disabled = !sourceReady();
}

function progress(fraction) {
  $("upload").hidden = false;
  $("upload-bar").style.transform = `scaleX(${fraction})`;
  $("upload-text").textContent = `${t("uploading")} ${Math.round(fraction * 100)}%`;
}

async function send(options) {
  if (pageMode && state.file) return upload(state.file, options, progress);
  const url = pageMode ? $("link").value.trim() : state.url;
  return post("/jobs", { url, ...options });
}

async function submit(event) {
  event.preventDefault();
  if (!sourceReady()) return;
  const options = choices();
  await remember(options);
  $("go").disabled = true;
  $("go").textContent = t("sending");
  try {
    await send(options);
    $("notice").textContent = t("started");
    clearSource();
  } catch (error) {
    return error.kind === "token" ? show("pair") : connect();
  } finally {
    $("go").textContent = t("translate");
    $("upload").hidden = true;
    refreshButton();
  }
}

function clearSource() {
  if (!pageMode) return;
  state.file = null;
  $("file").value = "";
  $("link").value = "";
  $("drop-file").hidden = true;
}

function takeFile(file) {
  if (!isMedia(file)) {
    $("notice").textContent = t("badFile");
    return;
  }
  state.file = file;
  $("notice").textContent = "";
  $("drop-file").hidden = false;
  $("drop-file").textContent = file.name;
  refreshButton();
}

function wireDrop() {
  const zone = $("drop-zone");
  $("file").addEventListener("change", () => takeFile($("file").files[0]));
  zone.addEventListener("dragover", (event) => { event.preventDefault(); zone.classList.add("over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("over"));
  zone.addEventListener("drop", (event) => {
    event.preventDefault();
    zone.classList.remove("over");
    takeFile(event.dataTransfer.files[0]);
  });
  $("link").addEventListener("input", refreshButton);
}

async function pair(event) {
  event.preventDefault();
  await remember({ token: $("token").value.trim() });
  try {
    await api("/jobs");
    $("pair-error").hidden = true;
    await openMain();
  } catch {
    $("pair-error").hidden = false;
  }
}

async function openSettings() {
  clearInterval(state.poll);
  const saved = await settings();
  $("server").value = saved.server;
  $("settings-token").value = saved.token;
  show("settings");
}

async function saveSettings(event) {
  event.preventDefault();
  await remember({ server: $("server").value.trim(), token: $("settings-token").value.trim() });
  $("settings-notice").textContent = t("saved");
}

function wire() {
  $("order").addEventListener("submit", submit);
  $("target").addEventListener("change", syncDialect);
  $("open-file-page").addEventListener("click", () => {
    chrome.tabs.create({ url: chrome.runtime.getURL("app.html?page=1") });
    window.close();
  });
  $("retry-connect").addEventListener("click", connect);
  $("pair-form").addEventListener("submit", pair);
  $("open-settings").addEventListener("click", openSettings);
  $("settings-form").addEventListener("submit", saveSettings);
  $("close-settings").addEventListener("click", connect);
  wireDrop();
}

applyText();
wire();
if (params.get("view") === "settings") openSettings();
else connect();
