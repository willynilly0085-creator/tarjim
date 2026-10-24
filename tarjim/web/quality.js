// The qualities a pasted link offers, read by the engine before anything downloads. 1080p, or
// the nearest below it, is chosen each time; "sound only" is offered for a subtitle file alone.
import { $, post } from "./api.js";
import { t } from "./i18n.js";

const MB = 1024 * 1024;
const WAIT = 400;
const state = { asked: "", found: null, error: "", soundOnly: false, timer: 0, changed: () => {} };

export function sizeText(bytes) {
  if (bytes >= 1024 * MB) return t("sizeGb", { n: (bytes / (1024 * MB)).toFixed(1) });
  return t("sizeMb", { n: Math.max(1, Math.round(bytes / MB)) });
}

function option(id, label, bytes) {
  const tooBig = bytes > state.found.limit;
  const text = tooBig ? t("qualityTooBig", { label }) : bytes ? t("qualityRow", { label, size: sizeText(bytes) }) : label;
  return Object.assign(new Option(text, id), { disabled: tooBig });
}

function options() {
  const { choices, audio } = state.found;
  const rows = choices.map((choice) => option(choice.id, choice.label, choice.size));
  return audio && state.soundOnly ? [...rows, option("audio", t("qualityAudio"), audio.size)] : rows;
}

// The video's title keeps its own direction inside a page of the other direction.
function note(text, isError = false, own = false) {
  $("quality-note").replaceChildren(own ? Object.assign(document.createElement("bdi"), { textContent: text }) : text);
  $("quality-note").classList.toggle("error", isError);
  $("quality-note").classList.toggle("meta", !isError);
}

function render() {
  const select = $("quality");
  const kept = select.value;
  const offered = Boolean(state.found?.choices.length);
  $("quality-field").hidden = !state.asked || (Boolean(state.found) && !offered);
  select.hidden = !offered;
  if (state.error) return note(t(state.error === "list" ? "err_list" : "qualityFailed"), state.error === "list");
  if (!state.found) return note(t("qualityReading"));
  if (!offered) return note("");
  select.replaceChildren(...options());
  const usable = [...select.options].find((o) => o.value === kept && !o.disabled);
  select.value = usable ? kept : state.found.default;
  note(state.found.title, false, true);
}

async function ask(url) {
  Object.assign(state, { asked: url, found: null, error: "" });
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

function heard(url) {
  clearTimeout(state.timer);
  if (!/^https?:\/\/\S+$/i.test(url)) return forgetQuality();
  if (url !== state.asked) state.timer = setTimeout(() => ask(url), WAIT);
}

export function watchQuality(input, changed) {
  state.changed = changed;
  input.addEventListener("input", () => heard(input.value.trim()));
}

export function soundOnly(allowed) {
  if (allowed === state.soundOnly) return;
  state.soundOnly = allowed;
  if (state.found) render();
}

// The rows are written in the interface's language; a new language writes them again.
export const repaintQuality = () => state.asked && render();

export function forgetQuality() {
  clearTimeout(state.timer);
  Object.assign(state, { asked: "", found: null, error: "" });
  render();
  state.changed();
}

// Nothing while the qualities are read: the engine then takes 1080p or the nearest below it.
export const chosenQuality = () => (state.found?.choices.length ? $("quality").value : "");
export const qualityBlocked = () => state.error === "list";
