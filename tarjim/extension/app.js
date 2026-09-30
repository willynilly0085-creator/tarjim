import { watchJobs } from "./jobs.js";
import { api, loadWords, post, remember, settings, t, uiDirection, uiLanguage } from "./shared.js";
import { downloadable } from "./posts.js";
import { $, show } from "./dom.js";
import { claimPending } from "./pairing.js";
import { autoPair, openSettings, wirePanels } from "./panels.js";
import { isMedia, upload } from "./upload.js";

const params = new URLSearchParams(location.search);
const pageMode = params.get("page") === "1";
const state = { url: "", file: null, languages: new Map(), poll: 0 };

function applyText() {
  document.documentElement.lang = uiLanguage();
  document.documentElement.dir = uiDirection();
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-label]").forEach((el) => {
    el.setAttribute("aria-label", t(el.dataset.i18nLabel));
    el.title = t(el.dataset.i18nLabel);
  });
  document.body.classList.toggle("page", pageMode);
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
  await claimPending();
  try {
    await api("/jobs");
  } catch (error) {
    return show(error.kind === "token" ? "pair" : "offline");
  }
  const setup = await api("/setup").catch(() => ({}));
  if (setup.setup_done !== "yes") return show("setup");
  await openMain();
}

async function loadLanguages(target) {
  const select = $("target");
  const languages = await api("/languages");
  state.languages = new Map(languages.map((l) => [l.code, l.native]));
  select.replaceChildren(...languages.map((l) => new Option(l.native, l.code, false, l.code === target)));
}

function syncDialect() {
  const arabic = $("target").value === "ar";
  $("dialect-field").hidden = !arabic;
  $("voice-narrator").hidden = !arabic;
  if (!arabic && $("voice").value === "fishvoice") $("voice").value = "clone";
}

function persist() {
  remember({ ...choices(), voice: $("voice").value });
}

async function describeSource() {
  if (pageMode) {
    $("source-tab").hidden = true;
    $("drop").hidden = false;
    $("open-file-page").hidden = true;
    return;
  }
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const usable = downloadable(tab?.url);
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
  const [output, dubVoice] = saved.mode.startsWith("dub-") ? ["dub", saved.mode.slice(4)] : [saved.mode, saved.voice];
  document.querySelector(`input[name=mode][value=${output}]`).checked = true;
  $("voice").value = dubVoice || "gemini";
  syncDialect();
  syncVoice();
  await describeSource();
  refreshButton();
  state.poll = watchJobs(state.languages);
}

function choices() {
  const form = $("order");
  const output = form.mode.value;
  const mode = output === "dub" ? `dub-${$("voice").value}` : output;
  return { target: $("target").value, dialect: form.dialect.value, mode };
}

function syncVoice() {
  $("voice-field").hidden = $("order").mode.value !== "dub";
}

function sourceReady() {
  return pageMode ? Boolean(state.file) || downloadable($("link").value.trim()) : Boolean(state.url);
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
  await remember({ ...options, voice: $("voice").value });
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

function wire() {
  $("order").addEventListener("submit", submit);
  $("target").addEventListener("change", syncDialect);
  $("order").addEventListener("change", persist);
  document.querySelectorAll("input[name=mode]").forEach((el) => el.addEventListener("change", syncVoice));
  $("open-file-page").addEventListener("click", () => {
    chrome.tabs.create({ url: chrome.runtime.getURL("app.html?page=1") });
    window.close();
  });
  wirePanels({ ready: openMain, back: connect, leave: () => clearInterval(state.poll) });
  wireDrop();
}

await loadWords();
applyText();
wire();
if (params.get("view") === "settings") openSettings();
else if (params.get("pair") === "auto") autoPair(openMain);
else connect();
