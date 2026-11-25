// The settings page, #prefs (2026-11-09): seven tabs of the engine's own settings table, each
// saved on its own 400 ms after a change, refused inline with the engine's Arabic reason, and
// greyed with the reason when it does nothing with the others as they are. Since 2026-11-25 the
// tabs sit in the grouped list both settings pages share (settings_nav.js), the subtitle tabs
// in titled parts, and the ready sets only on the two tabs they change.
import { $, api, post } from "./api.js";
import { t } from "./i18n.js";
import { button, el } from "./ui.js";
import { field } from "./prefs_fields.js";
import { followLanguage, generalTab } from "./prefs_general.js";
import { makePresets, resetGroups, resetKeys } from "./prefs_presets.js";
import { makePreview } from "./prefs_preview.js";
import { autosaver, failedWords, savedWords } from "./prefs_save.js";
import { TABS } from "./prefs_words.js";
import { hasParts, parts } from "./prefs_parts.js";
import { isSetup, markCurrent, navName, settingsNav } from "./settings_nav.js";

const page = { state: null, language: "ar", tab: "look", fields: new Map(), local: {}, refused: {},
  fonts: [], languages: [], hooks: {} };
const status = el("p", { className: "meta prefs-status", role: "status" });
const say = (text) => { status.textContent = text; };

const saver = autosaver({
  send: (values) => post("/prefs", { values, language: page.language }),
  done: async (answer, values) => {
    Object.keys(values).forEach((key) => { delete page.refused[key]; });
    Object.assign(page.refused, answer.refused || {});
    await reload();
    say(savedWords(answer, t));
  },
  failed: async (error) => { say(failedWords(error, t)); await reload().catch(() => {}); },
});

// All three are drawn again in the page's language whenever it changes (frame).
let preview = null;
let presets = null;
let nav = null;

function change(key, value) {
  page.local[key] = value;
  delete page.refused[key];
  page.fields.get(key)?.mark(markOf(key));
  say(t("prefsSaving"));
  saver.put(key, value);
  preview.draw(page.local, page.language);
}

function markOf(key) {
  const { changed, idle } = page.state;
  return { changed: changed.includes(key), idle: idle[key] || "", refused: page.refused[key] || "" };
}

// Back to the original, then fresh values; the status says whether it worked.
async function goBack(work) {
  await saver.flush();
  const done = await work().then(() => true, () => false);
  await reload().catch(() => {});
  say(t(done ? "prefsResetDone" : "prefsFailed"));
}

function resetOne(key) {
  delete page.refused[key];
  return goBack(() => resetKeys([key], page.language));
}

// Fresh values from the engine; a field the person is still changing keeps what they chose.
export async function reload() {
  page.state = await api(`/prefs?lang=${encodeURIComponent(page.language)}`);
  const before = page.local;
  page.local = { ...page.state.values };
  Object.keys(before).filter((key) => saver.waiting(key)).forEach((key) => { page.local[key] = before[key]; });
  for (const [key, one] of page.fields) {
    if (!saver.waiting(key)) one.set(page.state.values[key]);
    one.mark(markOf(key));
  }
  presets.draw();
  preview.draw(page.local, page.language);
}

const place = () => page.languages.find((l) => l.code === page.language)?.native || page.language;

function make(spec) {
  const one = field(spec, page.local[spec.key], { change, reset: resetOne, fonts: page.fonts,
    place: place(), language: page.language });
  one.mark(markOf(spec.key));
  page.fields.set(spec.key, one);
  return one.node;
}

const specsOf = (tab) => page.state.specs.filter((spec) => tab.groups.includes(spec.group));

// A tab in parts (prefs_parts.js), or one list with its finer settings in one fold.
function fieldsOf(tab) {
  const specs = specsOf(tab);
  if (hasParts(tab.id)) return parts(tab.id, specs, make);
  const advanced = specs.filter((spec) => spec.tier === "advanced").map(make);
  const more = el("details", { className: "prefs-advanced", hidden: !advanced.length },
    el("summary", { textContent: t("prefsAdvanced") }), el("div", { className: "pref-list" }, advanced));
  return [el("div", { className: "pref-list" }, specs.filter((spec) => spec.tier === "basic").map(make)), more];
}

function languagePicker() {
  const menu = el("select", { id: "prefs-language", className: "select compact" },
    page.languages.map((l) => new Option(l.native, l.code, false, l.code === page.language)));
  menu.addEventListener("change", async () => {
    await saver.flush();
    page.language = menu.value;
    await fonts();
    await reload();
    showTab(page.tab);
  });
  return el("div", { className: "prefs-language" },
    el("label", { htmlFor: menu.id, textContent: t("prefsFor") }), menu);
}

function settingsPanel(tab) {
  page.fields.clear();
  const local = specsOf(tab).some((s) => s.per_language);
  const again = button(t("prefsResetTab"), () => goBack(() => resetGroups(tab.groups, page.language)),
    "text-link reset-tab");
  const column = el("div", { className: "prefs-fields" }, tab.preview ? presets.node : "",
    local ? languagePicker() : "", fieldsOf(tab), again);
  const body = el("div", { className: "prefs-body" }, column);
  if (tab.preview) body.prepend(preview.node);
  body.classList.toggle("with-preview", Boolean(tab.preview));
  return body;
}

const panelTitle = (id) => el("h2", { className: "panel-heading", id: "prefs-panel-title", textContent: navName(id), tabIndex: -1 });

// A setup section leaves this page for the setup's own (main.js); a tab is drawn here.
async function showTab(id, byKey = false) {
  if (isSetup(id)) return page.hooks.open(id, byKey);
  page.tab = id;
  markCurrent(nav, id, byKey);
  const panel = $("prefs-panel");
  if (id === "general") {
    page.fields.clear();
    panel.replaceChildren(panelTitle(id), await generalTab({ ...page.hooks, say }));
    return;
  }
  panel.replaceChildren(panelTitle(id), settingsPanel(TABS.find((one) => one.id === id)));
  preview.draw(page.local, page.language);
}

async function fonts() {
  const found = await api(`/prefs/fonts?lang=${encodeURIComponent(page.language)}`).catch(() => ({ fonts: [] }));
  page.fonts = found.fonts || [];
}

function frame() {
  preview = makePreview({ real: (portrait) => post("/prefs/preview",
    { values: page.local, language: page.language, portrait }) });
  presets = makePresets({ state: () => page.state, reload: () => reload(), say });
  nav = settingsNav(() => page.tab, showTab, "prefs");
  const back = button(t("back"), () => page.hooks.close?.(), "button-quiet prefs-back");
  const panel = el("section", { id: "prefs-panel", className: "prefs-panel" });
  panel.setAttribute("aria-labelledby", "prefs-panel-title");
  $("prefs").replaceChildren(
    el("div", { className: "prefs-head" }, el("h1", { textContent: t("prefsTitle"), tabIndex: -1 }), presets.whole, back),
    el("div", { className: "settings-shell" }, nav, panel), el("div", { className: "prefs-foot" }, status));
}

// hooks: { close(), open(section, byKey), language(code) }; language: the target to start with;
// tab: the tab to open on, else the last one shown.
export async function openPrefs(hooks, language = "ar", tab = page.tab) {
  page.hooks = { ...hooks, language: async (code) => { await hooks.language(code); followLanguage(code); } };
  page.language = language;
  page.tab = tab;
  ["wizard", "assistant", "workspace"].forEach((id) => { $(id).hidden = true; });
  $("prefs").hidden = false;
  page.languages = await api("/languages").catch(() => []);
  await fonts();
  frame();
  say("");
  await reload();
  await showTab(page.tab);
  $("prefs").querySelector("h1").focus?.();
}

export async function leavePrefs() {
  await saver.flush();
  $("prefs").hidden = true;
}

// The page's language changed: words are drawn again, values stay.
export function repaintPrefs() {
  if ($("prefs").hidden || !page.state) return;
  frame();
  presets.draw();
  showTab(page.tab);
}
