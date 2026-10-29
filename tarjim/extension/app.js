import { watchJobs } from "./jobs.js";
import {
  api, loadWords, remember, settings, startJob, t, uiDirection, uiLanguage, wakeEngine,
} from "./shared.js";
import { downloadable } from "./posts.js";
import { chosenQuality, forgetQuality, heardLink, onQuality, qualityBlocked, soundOnly } from "./quality.js";
import { clearPending, describeSource } from "./source.js";
import { $, show } from "./dom.js";
import { showEngine } from "./engine.js";
import { claimPending } from "./pairing.js";
import { showLinkedVoices } from "./keys.js";
import { autoPair, openSettings, showPair, wirePanels } from "./panels.js";
import { isMedia, sendProblem, showProgress, tooBig, upload } from "./upload.js";

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
  document.body.classList.toggle("windows", navigator.userAgent.includes("Windows"));
}

function linkState(online) {
  $("link-state").dataset.state = online ? "online" : "offline";
  $("link-text").textContent = t(online ? "statusOnline" : "statusOffline");
}

// A stopped engine is started from here when tarjim registered the way to (shared.js wakeEngine);
// the offline panel says so while it starts, and stays only if it could not.
async function reachEngine() {
  if (await api("/ping").then(() => true, () => false)) return true;
  linkState(false);
  show("offline");
  $("offline-note").textContent = t("waking");
  const woken = await wakeEngine();
  $("offline-note").textContent = "";
  return woken;
}

async function connect() {
  clearInterval(state.poll);
  if (!(await reachEngine())) return show("offline");
  linkState(true);
  await claimPending();
  try {
    await api("/jobs");
  } catch (error) {
    return error.kind === "token" ? showPair() : show("offline");
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

const persist = () => remember({ ...choices(), voice: $("voice").value });

async function openMain() {
  show("main");
  const saved = await settings();
  await loadLanguages(saved.target);
  document.querySelector(`input[name=dialect][value=${saved.dialect}]`).checked = true;
  const [output, dubVoice] = saved.mode.startsWith("dub-") ? ["dub", saved.mode.slice(4)] : [saved.mode, saved.voice];
  document.querySelector(`input[name=mode][value=${output}]`).checked = true;
  $("voice").value = dubVoice || "gemini";
  await Promise.all([showLinkedVoices($("voice")), showEngine()]);
  syncDialect();
  syncVoice();
  state.url = await describeSource(pageMode);
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
  soundOnly($("order").mode.value === "srt");
}

function sourceReady() {
  if (pageMode && state.file) return true;
  return !qualityBlocked() && (pageMode ? downloadable($("link").value.trim()) : Boolean(state.url));
}

const refreshButton = () => { $("go").disabled = !sourceReady(); };

async function send(options) {
  if (pageMode && state.file) return upload(state.file, options, showProgress);
  const url = pageMode ? $("link").value.trim() : state.url;
  return startJob({ url, ...options, quality: chosenQuality() });
}

async function submit(event) {
  event.preventDefault();
  if (!sourceReady()) return;
  const options = choices();
  await remember({ ...options, voice: $("voice").value });
  $("go").disabled = true;
  $("go").textContent = t("sending");
  $("notice").textContent = "";
  try {
    await send(options);
    $("notice").textContent = t("started");
    await clearPending();
    clearSource();
  } catch (error) {
    if (error.kind === "token") return showPair();
    if (error.kind === "offline") return connect();
    $("notice").textContent = sendProblem(error, state.languages.get(options.target));  // e.g. a link it cannot take
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
  forgetQuality();
  $("drop-file").hidden = true;
}

function takeFile(file) {
  if (!isMedia(file) || tooBig(file)) {
    $("notice").textContent = t(isMedia(file) ? "sendTooBig" : "badFile");
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
  $("link").addEventListener("input", () => {
    heardLink($("link").value.trim());
    refreshButton();
  });
}

function wire() {
  onQuality(refreshButton);
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
