// The "عام" tab (2026-11-09): the page's language, starting with the computer and updating on
// its own, each through the route the setup already uses, and a way into engines, keys, voices
// and tools, which stay in setup and are never part of the settings or of a preset.
import { $, api, post } from "./api.js";
import { t } from "./i18n.js";
import { button, el } from "./ui.js";

function check(id, words, checked, save) {
  const input = el("input", { type: "checkbox", id, className: "switch-input", checked });
  input.setAttribute("role", "switch");
  input.addEventListener("change", () => save(input.checked));
  return el("div", { className: "pref" },
    el("div", { className: "pref-head" }, el("label", { className: "pref-label", htmlFor: id, textContent: words })),
    el("div", { className: "pref-control" }, el("span", { className: "switch" }, input, el("span", { className: "switch-track" }))));
}

function language(setup, changed) {
  const menu = el("select", { id: "prefs-ui-language", className: "select" },
    (setup.ui_languages || []).map((l) => Object.assign(new Option(l.name, l.code, false, l.code === document.documentElement.lang), { lang: l.code })));
  menu.addEventListener("change", () => changed(menu.value));
  return el("div", { className: "pref" },
    el("div", { className: "pref-head" }, el("label", { className: "pref-label", htmlFor: menu.id, textContent: t("uiLanguage") })),
    el("div", { className: "pref-control" }, menu));
}

// hooks: { language(code), engines(setup), say(text) }
export async function generalTab(hooks) {
  const setup = await api("/setup");
  const saved = (work) => async (value) => {
    try {
      await work(value);
      hooks.say(t("prefsSaved"));
    } catch {
      hooks.say(t("prefsFailed"));
    }
  };
  const engines = el("div", { className: "pref engines-link" },
    el("div", { className: "pref-head" }, el("span", { className: "pref-label", textContent: t("prefsEngines") })),
    el("p", { className: "pref-hint", textContent: t("prefsEnginesHint") }),
    button(t("prefsOpenEngines"), () => hooks.engines(setup)));
  return el("div", { className: "pref-list" },
    language(setup, saved(hooks.language)),
    check("prefs-autostart", t("autostart"), Boolean(setup.autostart), saved((on) => post("/setup", { autostart: on }))),
    check("prefs-auto-update", t("autoUpdate"), setup.auto_update !== false,
      saved((on) => post("/setup", { auto_update: on }))),
    engines);
}

// The header's language menu follows a change made here.
export const followLanguage = (code) => { if ($("ui-language")) $("ui-language").value = code; };
