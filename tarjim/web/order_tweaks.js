// "تعديلات لهالفيديو بس" on the order form (2026-11-09): the settings used most, and any other
// setting that may change for one video, sent with the order as its own changes and never saved.
// The engine checks them with the same gate as a save and refuses the order before it starts,
// with each change's reason shown under it here.
import { $, api } from "./api.js";
import { t } from "./i18n.js";
import { button, el } from "./ui.js";
import { field } from "./prefs_fields.js";
import { label } from "./prefs_words.js";

const MOST_USED = ["look.style", "look.size_wide", "look.size_tall", "look.position", "text.reading_cps",
  "translate.register", "output.burn_with_dub"];
const state = { saved: {}, specs: [], shown: [], tweaks: {}, refused: {}, fields: new Map(), target: "" };
const box = el("div", { className: "pref-list" });
const count = el("span", { className: "meta" });
const more = el("div", { className: "tweaks-more" });

export const tweaks = () => ({ ...state.tweaks });

function change(key, value) {
  if (String(value) === String(state.saved[key])) delete state.tweaks[key];
  else state.tweaks[key] = value;
  delete state.refused[key];
  mark();
}

function reset(key) {
  delete state.tweaks[key];
  delete state.refused[key];
  state.fields.get(key)?.set(state.saved[key]);
  mark();
}

function mark() {
  for (const [key, one] of state.fields) one.mark({ changed: key in state.tweaks, refused: state.refused[key] || "" });
  const n = Object.keys(state.tweaks).length;
  count.textContent = n ? t("tweaksCount", { n }) : "";
}

function others() {
  const left = state.specs.filter((spec) => spec.per_job && !state.shown.includes(spec.key));
  const pick = el("select", { className: "select", id: "tweaks-pick" },
    new Option(t("tweaksMore"), ""), left.map((spec) => new Option(label(spec), spec.key)));
  pick.setAttribute("aria-label", t("tweaksMore"));
  pick.addEventListener("change", () => {
    if (!pick.value) return;
    state.shown.push(pick.value);
    draw();
    $("tweaks-pick").focus();
  });
  const clear = button(t("tweaksClear"), () => { state.tweaks = {}; state.refused = {}; draw(); });
  more.replaceChildren(pick, clear);
}

function draw() {
  state.fields.clear();
  const specs = state.shown.map((key) => state.specs.find((spec) => spec.key === key)).filter(Boolean);
  box.replaceChildren(...specs.map((spec) => {
    // The person's own saved value is this video's original, not tarjim's.
    const saved = { ...spec, default: state.saved[spec.key] };
    const one = field(saved, state.tweaks[spec.key] ?? state.saved[spec.key], { change, reset, fonts: [],
      place: "", language: state.target });
    state.fields.set(spec.key, one);
    return one.node;
  }));
  others();
  mark();
}

// The settings in force for the order's language, the starting point of its own changes.
async function load(target) {
  state.target = target;
  try {
    const now = await api(`/prefs?lang=${encodeURIComponent(target)}`);
    Object.assign(state, { saved: now.values, specs: now.specs });
  } catch {
    Object.assign(state, { saved: {}, specs: [] });
  }
  if (!state.shown.length) state.shown = [...MOST_USED];
  draw();
}

export const loadTweaks = (target) => load(target);
export const repaintTweaks = () => draw();

export function clearTweaks() {
  Object.assign(state, { tweaks: {}, refused: {}, shown: [...MOST_USED] });
  draw();
  $("order-tweaks").open = false;
}

// A refused order: each change's reason under it, and the disclosure opened to show them.
export function showTweakRefusals(error) {
  const refused = error?.body?.error === "tweaks" ? error.body.refused || {} : {};
  if (!Object.keys(refused).length) return;
  state.refused = refused;
  mark();
  $("order-tweaks").open = true;
}

export function watchTweaks(target) {
  const details = el("details", { className: "order-tweaks", id: "order-tweaks" },
    el("summary", {}, el("span", { textContent: t("tweaksTitle") }), " ", count),
    el("p", { className: "meta", textContent: t("tweaksHint") }), box, more);
  details.querySelector("summary span").dataset.t = "tweaksTitle";
  details.querySelector("p").dataset.t = "tweaksHint";
  $("engine").before(details);
  target.addEventListener("change", () => load(target.value));
  details.addEventListener("toggle", () => { if (details.open && !state.specs.length) load(target.value); });
  return load(target.value || "ar");
}
