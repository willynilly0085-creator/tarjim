import { $, api, post, upload } from "./api.js";
import { showEngine } from "./engine.js";
import { t } from "./i18n.js";
import { watchJobs } from "./jobs.js";
import { recalledTarget, recallForm, recallVoice, remember } from "./order_memory.js";
import { problem } from "./problems.js";
import { chosenQuality, forgetQuality, qualityBlocked, soundOnly, watchQuality } from "./quality.js";
import { showUpdate } from "./update.js";
import { hasKey, linkedVoices, loadVoices, speechName, voicesKnown } from "./voices.js";

const MEDIA = /\.(mp4|mkv|webm|mov|avi|m4v|mp3|m4a|wav|flac|ogg|opus|aac)$/i;
const LARGEST = 8 * 1024 ** 3;  // the engine's own limit for an upload (server/app.py)
const state = { file: null, poll: 0, wired: false, recalled: false, languages: new Map() };
const LINKED = { eleven: "voiceEleven", elevenclone: "voiceElevenClone", speech: "voiceSpeech" };
const KEYED = { gemini: "gemini", fish: "fish", fishvoice: "fish" };
const SEND = { "bad url": "sendBadLink", file: "sendFileBroken", big: "sendTooBig",
  dub_language: "sendDubLanguage", dub_key: "sendDubKey", list: "err_list", mode: "actionFailed" };

const linkReady = () => /^https?:\/\//i.test($("link").value.trim()) && !qualityBlocked();
const ready = () => Boolean(state.file) || linkReady();

function say(text, isError = false) {
  $("notice").textContent = text;
  $("notice").classList.toggle("error", isError);
}

function sync() {
  const form = $("order");
  const arabic = $("target").value === "ar";
  $("dialect-field").hidden = !arabic;
  $("voice-narrator").hidden = !arabic;
  if (!arabic && $("voice").value === "fishvoice") $("voice").value = "clone";
  $("voice-field").hidden = form.mode.value !== "dub";
  soundOnly(form.mode.value === "srt");
  $("go").disabled = !ready();
}

// A voice that needs a key nobody saved stays in the list, marked and not choosable, so the
// job is never dubbed in another voice without the person knowing.
function markVoices() {
  if (!voicesKnown()) return;
  for (const option of $("voice").options) {
    if (!KEYED[option.value]) continue;
    option.disabled = !hasKey(KEYED[option.value]);
    option.textContent = option.disabled ? `${t(option.dataset.t)} · ${t("needsKey")}` : t(option.dataset.t);
  }
  if ($("voice").selectedOptions[0]?.disabled) $("voice").value = "clone";
}

// Voices from a service the person linked with their own key appear once it is linked.
async function showLinkedVoices() {
  await loadVoices();
  $("voice").querySelectorAll("[data-linked]").forEach((option) => option.remove());
  for (const id of linkedVoices()) {
    const named = id === "speech" && speechName();
    const option = new Option(named ? t("voiceLinked", { name: speechName() }) : t(LINKED[id]), id);
    Object.assign(option.dataset, named ? { linked: "yes" } : { t: LINKED[id], linked: "yes" });
    $("voice").append(option);
  }
  markVoices();
  $("voice-more").hidden = linkedVoices().length > 0 && [...$("voice").options].every((o) => !o.disabled);
}

function showFile(file) {
  state.file = file;
  $("drop-file-row").hidden = !file;
  $("drop-file").textContent = file ? file.name : "";
  if (!file) $("file").value = "";
}

// The last thing the person gave wins: a file sets a pasted link aside, and a link a file.
function take(file) {
  if (!file) return;
  if (!MEDIA.test(file.name)) return say(t("badFile"), true);
  if (file.size > LARGEST) return say(t("sendTooBig"), true);
  showFile(file);
  say("");
  if ($("link").value) {
    $("link").value = "";
    forgetQuality();
  }
  sync();
}

function choices() {
  const form = $("order");
  const output = form.mode.value;
  return { target: $("target").value, dialect: form.dialect.value, mode: output === "dub" ? `dub-${$("voice").value}` : output };
}

function progress(fraction) {
  $("upload").hidden = false;
  $("upload-bar").style.transform = `scaleX(${fraction})`;
  $("upload-text").textContent = `${t("uploading")} ${Math.round(fraction * 100)}%`;
}

// A file is checked before it is sent, so a refused order does not wait for gigabytes to move.
async function send() {
  if (!state.file) return post("/jobs", { url: $("link").value.trim(), ...choices(), quality: chosenQuality() });
  await post("/jobs/check", choices());
  return upload(state.file, choices(), progress);
}

function sent() {
  say(t("started"));
  showFile(null);
  $("link").value = "";
  forgetQuality();
}

async function submit(event) {
  event.preventDefault();
  if (!ready()) return;
  $("go").disabled = true;
  $("go").textContent = t("sending");
  try {
    await send();
    sent();
  } catch (error) {
    say(problem(error, SEND, { language: state.languages.get($("target").value) || "" }), true);
  } finally {
    $("go").textContent = t("translate");
    $("upload").hidden = true;
    sync();
  }
}

// A file let go anywhere on the page is taken, never opened by the browser in place of tarjim.
function catchDrops() {
  window.addEventListener("dragover", (event) => event.preventDefault());
  window.addEventListener("drop", (event) => {
    event.preventDefault();
    $("drop-zone").classList.remove("over");
    if (!$("workspace").hidden) take(event.dataTransfer?.files[0]);
  });
}

function wire() {
  const zone = $("drop-zone");
  $("file").addEventListener("change", () => take($("file").files[0]));
  zone.addEventListener("dragover", () => zone.classList.add("over"));
  zone.addEventListener("dragleave", () => zone.classList.remove("over"));
  catchDrops();
  $("drop-clear").addEventListener("click", () => { showFile(null); sync(); $("file").focus(); });
  $("order").addEventListener("change", () => { sync(); remember(); });
  $("link").addEventListener("input", () => { if ($("link").value.trim()) showFile(null); sync(); });
  watchQuality($("link"), sync);
  $("order").addEventListener("submit", submit);
  state.wired = true;
}

async function fillLanguages() {
  const languages = await api("/languages");
  state.languages = new Map(languages.map((l) => [l.code, l.native]));
  const current = $("target").value || recalledTarget() || (document.documentElement.lang === "ar" ? "ar" : "en");
  $("target").replaceChildren(...languages.map((l) => new Option(l.native, l.code, false, l.code === current)));
}

// The recent jobs do not wait for the voices or the translator, which may ask services online.
export async function openWorkspace() {
  $("wizard").hidden = true;
  $("assistant").hidden = true;
  $("workspace").hidden = false;
  $("open-settings").hidden = false;
  if (!state.wired) wire();
  showUpdate();
  await fillLanguages();
  clearInterval(state.poll);
  state.poll = watchJobs(state.languages);
  const first = !state.recalled;
  state.recalled = true;
  if (first) recallForm();
  sync();
  await Promise.all([showLinkedVoices(), showEngine()]);
  if (first) recallVoice();
  sync();
}

export const repaintWorkspace = () => markVoices();
