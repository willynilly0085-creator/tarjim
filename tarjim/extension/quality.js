// The qualities a link offers, read by tarjim before anything downloads (the page's own
// web/quality.js, in the extension's words). 1080p, or the nearest below it, is chosen each time;
// "sound only" is offered for a subtitle file alone.
import { $ } from "./dom.js";
import { post, t } from "./shared.js";

const MB = 1024 * 1024;
const WAIT = 400;
const state = { asked: "", found: null, error: "", soundOnly: false, titled: false, timer: 0, changed: () => {} };

// A size keeps its number before its unit in a right-to-left sentence too.
function sizeText(bytes) {
  const size = bytes >= 1024 * MB ? t("sizeGb", (bytes / (1024 * MB)).toFixed(1))
    : t("sizeMb", String(Math.max(1, Math.round(bytes / MB))));
  return `⁦${size}⁩`;
}

function option(id, label, bytes) {
  const tooBig = bytes > state.found.limit;
  const text = tooBig ? t("qualityTooBig", label) : bytes ? t("qualityRow", label, sizeText(bytes)) : label;
  return Object.assign(new Option(text, id), { disabled: tooBig });
}

function options() {
  const { choices, audio } = state.found;
  const rows = choices.map((choice) => option(choice.id, choice.label, choice.size));
  return audio && state.soundOnly ? [...rows, option("audio", t("qualityAudio"), audio.size)] : rows;
}

function note(text, isError = false) {
  $("quality-note").textContent = text;
  $("quality-note").classList.toggle("error", isError);
  $("quality-note").classList.toggle("meta", !isError);
}

function render() {
  const select = $("quality");
  const kept = select.value;
  const offered = Boolean(state.found?.choices.length);
  $("quality-field").hidden = !state.asked || (Boolean(state.found) && !offered);
  select.hidden = !offered;
  if (state.error) return note(t(state.error === "list" ? "errList" : "qualityFailed"), state.error === "list");
  if (!state.found) return note(t("qualityReading"));
  if (!offered) return note("");
  select.replaceChildren(...options());
  const usable = [...select.options].find((o) => o.value === kept && !o.disabled);
  select.value = usable ? kept : state.found.default;
  note(state.titled ? state.found.title : "");
}

// titled: the video's title is shown under the qualities when nothing else on the screen names it.
export async function askQuality(url, titled = true) {
  Object.assign(state, { asked: url, found: null, error: "", titled });
  render();
  state.changed();
  let found = null;
  let error = "";
  try {
    found = await post("/links/qualities", { url });
  } catch (failure) {
    error = failure.body?.error === "list" ? "list" : "download";
  }
  if (state.asked !== url) return;
  Object.assign(state, { found, error });
  render();
  state.changed();
}

export function heardLink(url) {
  clearTimeout(state.timer);
  if (!/^https?:\/\/\S+$/i.test(url)) return forgetQuality();
  if (url !== state.asked) state.timer = setTimeout(() => askQuality(url), WAIT);
}

export function onQuality(changed) {
  state.changed = changed;
}

export function soundOnly(allowed) {
  if (allowed === state.soundOnly) return;
  state.soundOnly = allowed;
  if (state.found) render();
}

export function forgetQuality() {
  clearTimeout(state.timer);
  Object.assign(state, { asked: "", found: null, error: "" });
  render();
  state.changed();
}

// Nothing while the qualities are read: tarjim then takes 1080p or the nearest below it.
export const chosenQuality = () => (state.found?.choices.length ? $("quality").value : "");
export const qualityBlocked = () => state.error === "list";
export const qualityTitle = () => state.found?.title || "";
