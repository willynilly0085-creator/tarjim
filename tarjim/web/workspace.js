import { $, api, post, upload } from "./api.js";
import { t } from "./i18n.js";
import { watchJobs } from "./jobs.js";

const MEDIA = /\.(mp4|mkv|webm|mov|avi|m4v|mp3|m4a|wav|flac|ogg|opus|aac)$/i;
const state = { file: null, poll: 0, wired: false, languages: new Map() };

const linkReady = () => /^https?:\/\//i.test($("link").value.trim());
const ready = () => Boolean(state.file) || linkReady();

function sync() {
  const form = $("order");
  const arabic = $("target").value === "ar";
  $("dialect-field").hidden = !arabic;
  $("voice-narrator").hidden = !arabic;
  if (!arabic && $("voice").value === "fishvoice") $("voice").value = "clone";
  $("voice-field").hidden = form.mode.value !== "dub";
  $("go").disabled = !ready();
}

function take(file) {
  if (!file || !MEDIA.test(file.name)) {
    $("notice").textContent = t("badFile");
    return;
  }
  state.file = file;
  $("notice").textContent = "";
  $("drop-file").hidden = false;
  $("drop-file").textContent = file.name;
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

async function submit(event) {
  event.preventDefault();
  if (!ready()) return;
  $("go").disabled = true;
  $("go").textContent = t("sending");
  try {
    if (state.file) await upload(state.file, choices(), progress);
    else await post("/jobs", { url: $("link").value.trim(), ...choices() });
    $("notice").textContent = t("started");
    state.file = null;
    $("file").value = "";
    $("link").value = "";
    $("drop-file").hidden = true;
  } catch {
    $("notice").textContent = t("err_unknown");
  } finally {
    $("go").textContent = t("translate");
    $("upload").hidden = true;
    sync();
  }
}

function wire() {
  const zone = $("drop-zone");
  $("file").addEventListener("change", () => take($("file").files[0]));
  zone.addEventListener("dragover", (event) => { event.preventDefault(); zone.classList.add("over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("over"));
  zone.addEventListener("drop", (event) => { event.preventDefault(); zone.classList.remove("over"); take(event.dataTransfer.files[0]); });
  $("order").addEventListener("change", sync);
  $("link").addEventListener("input", sync);
  $("order").addEventListener("submit", submit);
  state.wired = true;
}

export async function openWorkspace() {
  $("wizard").hidden = true;
  $("workspace").hidden = false;
  $("open-settings").hidden = false;
  if (!state.wired) wire();
  const languages = await api("/languages");
  state.languages = new Map(languages.map((l) => [l.code, l.native]));
  const current = $("target").value || (document.documentElement.lang === "ar" ? "ar" : "en");
  $("target").replaceChildren(...languages.map((l) => new Option(l.native, l.code, false, l.code === current)));
  sync();
  clearInterval(state.poll);
  state.poll = watchJobs(state.languages);
}
