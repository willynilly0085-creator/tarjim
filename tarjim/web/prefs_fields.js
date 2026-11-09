// One setting on the page (2026-11-09): its label, one hint line, the original value in grey, a
// reset button once it differs, the reason a value was refused, and the reason it does nothing
// with the other settings as they are. A number is a slider held to the safe range, so a value
// out of it cannot even be typed; a choice of up to four is a row of segments.
import { t } from "./i18n.js";
import { el } from "./ui.js";
import { choiceName, hint, label, shown, withUnit } from "./prefs_words.js";

const MOST_SEGMENTS = 4;
const MOST_COLOURS = 6;
let made = 0;

const fresh = (key) => `pref-${key.replace(/\W/g, "-")}-${(made += 1)}`;
const numberOf = (spec, raw) => (Number.isInteger(spec.default) ? Math.round(Number(raw)) : Number(raw));
const readout = (spec, value) => withUnit(spec.key, value);

function slider(spec, id, said) {
  const input = el("input", { type: "range", id, min: spec.low, max: spec.high,
    step: spec.step || "any", className: "pref-range" });
  const out = el("output", { className: "pref-readout", htmlFor: id });
  input.addEventListener("input", () => {
    out.textContent = readout(spec, numberOf(spec, input.value));
    said(numberOf(spec, input.value));
  });
  const set = (value) => { input.value = String(value); out.textContent = readout(spec, value); };
  return { node: el("div", { className: "pref-slider" }, input, out), set, inputs: [input] };
}

function toggle(spec, id, said) {
  const input = el("input", { type: "checkbox", id, className: "switch-input" });
  input.setAttribute("role", "switch");
  input.addEventListener("change", () => said(input.checked));
  const node = el("span", { className: "switch" }, input, el("span", { className: "switch-track" }));
  return { node, set: (value) => { input.checked = Boolean(value); }, inputs: [input] };
}

// Numbers read in their own order (1, 3, 5), whatever the default listed first.
const ordered = (choices) => (choices.every((c) => typeof c === "number") ? [...choices].sort((a, b) => a - b) : choices);

function segments(spec, id, said) {
  spec = { ...spec, choices: ordered(spec.choices) };
  const radios = spec.choices.map((choice, at) => {
    const input = el("input", { type: "radio", name: id, value: String(at) });
    input.addEventListener("change", () => input.checked && said(spec.choices[at]));
    return input;
  });
  const node = el("div", { className: "segments pref-segments" },
    radios.map((input, at) => el("label", {}, input, el("span", { textContent: choiceName(spec, spec.choices[at]) }))));
  node.setAttribute("role", "radiogroup");
  const set = (value) => radios.forEach((input, at) => { input.checked = String(spec.choices[at]) === String(value); });
  return { node, set, inputs: radios };
}

function menu(spec, id, said, options = spec.choices) {
  const select = el("select", { id, className: "select" },
    options.map((choice, at) => new Option(choiceName(spec, choice), String(at))));
  select.addEventListener("change", () => said(options[Number(select.value)]));
  const set = (value) => { select.value = String(Math.max(0, options.findIndex((c) => String(c) === String(value)))); };
  return { node: select, set, inputs: [select] };
}

const HEX = /^#?[0-9a-f]{6}$/i;

function paint(spec, id, said) {
  const picker = el("input", { type: "color", id, className: "pref-colour" });
  const text = el("input", { type: "text", className: "text-input pref-hex", dir: "ltr", spellcheck: false,
    autocomplete: "off", maxLength: 7 });
  text.setAttribute("aria-label", `${label(spec)} (#RRGGBB)`);
  picker.addEventListener("input", () => { text.value = picker.value.toUpperCase(); said(text.value); });
  text.addEventListener("change", () => {
    if (HEX.test(text.value.trim())) picker.value = `#${text.value.trim().replace("#", "")}`.toLowerCase();
    said(text.value.trim());
  });
  const set = (value) => { text.value = String(value); if (HEX.test(String(value))) picker.value = String(value).toLowerCase(); };
  return { node: el("div", { className: "pref-paint" }, picker, text), set, inputs: [picker, text] };
}

function palette(spec, id, said) {
  const box = el("div", { className: "pref-palette" });
  let colours = [];
  const send = () => said(colours.join(","));
  const draw = () => {
    const pickers = colours.map((colour, at) => {
      const input = el("input", { type: "color", className: "pref-colour", value: colour.toLowerCase(),
        id: at === 0 ? id : "" });
      input.setAttribute("aria-label", t("prefsColourOf", { n: at + 2 }));
      input.addEventListener("input", () => { colours[at] = input.value.toUpperCase(); send(); });
      const drop = el("button", { type: "button", className: "pref-drop", textContent: "×",
        onclick: () => { colours.splice(at, 1); draw(); send(); } });
      drop.dataset.locked = String(colours.length === 1);
      drop.setAttribute("aria-label", t("prefsRemoveColour", { n: at + 2 }));
      return el("span", { className: "pref-swatch" }, input, drop);
    });
    const add = el("button", { type: "button", className: "button-quiet pref-add", textContent: t("prefsAddColour"),
      onclick: () => { colours.push(colours.at(-1)); draw(); send(); } });
    add.dataset.locked = String(colours.length >= MOST_COLOURS);
    [...pickers.map((p) => p.lastChild), add].forEach((b) => { b.disabled = b.dataset.locked === "true"; });
    box.replaceChildren(...pickers, add);
  };
  const set = (value) => { colours = String(value).split(",").filter(Boolean); draw(); };
  return { node: box, set, inputs: () => [...box.querySelectorAll("input"), ...box.querySelectorAll("button")] };
}

function words(spec, id, said) {
  const input = el("input", { type: "text", id, className: "text-input", dir: "ltr", spellcheck: false,
    autocomplete: "off" });
  input.addEventListener("change", () => said(input.value.trim()));
  return { node: input, set: (value) => { input.value = String(value); }, inputs: [input] };
}

// The font: the language's own, then every font this computer writes the language with.
function typeface(spec, id, said, fonts) {
  const options = [spec.default, ...fonts.filter((name) => name !== spec.default)];
  const control = menu(spec, id, said, options);
  control.node.options[0].textContent = t("prefsFontOwn", { font: spec.default });
  const set = control.set;
  control.set = (value) => {
    if (!options.includes(value)) {
      options.push(value);
      control.node.append(new Option(String(value), String(options.length - 1)));
    }
    set(value);
  };
  return control;
}

function control(spec, id, said, fonts) {
  if (spec.kind === "number") return slider(spec, id, said);
  if (spec.kind === "switch") return toggle(spec, id, said);
  if (spec.kind === "choice") {
    return spec.choices.length <= MOST_SEGMENTS ? segments(spec, id, said) : menu(spec, id, said);
  }
  if (spec.kind === "colour") return paint(spec, id, said);
  if (spec.kind === "colours") return palette(spec, id, said);
  if (spec.kind === "font") return typeface(spec, id, said, fonts || []);
  return words(spec, id, said);
}

function head(spec, id, reset, place) {
  const grouped = isGroup(spec);
  const name = el(grouped ? "span" : "label", { className: "pref-label", id: `${id}-label`, textContent: label(spec) });
  if (!grouped) name.htmlFor = id;
  const dot = el("span", { className: "pref-dot", title: t("prefsChanged") },
    el("span", { className: "visually-hidden", textContent: t("prefsChanged") }));
  const undo = el("button", { type: "button", className: "pref-reset", textContent: t("prefsReset"), onclick: reset });
  undo.setAttribute("aria-label", t("prefsResetLabel", { name: label(spec) }));
  const tag = spec.per_language && place ? el("span", { className: "pref-tag", textContent: place }) : "";
  return el("div", { className: "pref-head" }, name, tag, dot, undo);
}

// A colour or path inside an Arabic reason keeps its own order: "#F7F5F0", not "F7F5F0#".
const leftToRight = (text) => text.replace(/#[0-9a-f]{6}|[a-z]:\\[^\s«»]+/gi, (run) => `\u2066${run}\u2069`);

const isGroup = (spec) => spec.kind === "colours" || (spec.kind === "choice" && spec.choices.length <= MOST_SEGMENTS);

// Eastern digits are for Arabic only (2026-11-09): for another language the choice stays shown
// but cannot be picked, and the reason is said under it.
function lockEastern(spec, inputs, language) {
  if (spec.key === "translate.numbers" && language !== "ar") inputs[spec.choices.indexOf("eastern")].dataset.locked = "true";
}

// hooks: { change(key, value), reset(key), fonts, place, language }; place names the language.
export function field(spec, value, hooks) {
  const id = fresh(spec.key);
  const ctl = control(spec, id, (raw) => hooks.change(spec.key, raw), hooks.fonts);
  if (isGroup(spec)) ctl.node.setAttribute("aria-labelledby", `${id}-label`);
  const about = hint(spec);
  const original = el("span", { className: "pref-original", textContent: t("prefsOriginal", { value: shown(spec, spec.default) }) });
  const idle = el("p", { className: "pref-idle", hidden: true });
  const refusal = el("p", { className: "pref-refusal", role: "alert", hidden: true });
  const node = el("div", { className: "pref" }, head(spec, id, () => hooks.reset(spec.key), hooks.place),
    el("div", { className: "pref-control" }, ctl.node),
    el("p", { className: "pref-hint" }, about ? el("span", { textContent: about }) : "", original), idle, refusal);
  node.dataset.key = spec.key;
  ctl.set(value);
  const inputs = () => (typeof ctl.inputs === "function" ? ctl.inputs() : ctl.inputs);
  lockEastern(spec, inputs(), hooks.language);
  const result = { key: spec.key, spec, node, set: ctl.set,
    mark({ changed = false, idle: why = "", refused = "" } = {}) {
      Object.assign(node.dataset, { changed: String(changed), idle: String(Boolean(why)), refused: String(Boolean(refused)) });
      Object.assign(idle, { textContent: why, hidden: !why });
      Object.assign(refusal, { textContent: leftToRight(refused), hidden: !refused });
      const off = Boolean(why) && spec.key !== "translate.numbers";
      inputs().forEach((input) => { input.disabled = off || input.dataset.locked === "true"; });
    } };
  result.mark();
  return result;
}
