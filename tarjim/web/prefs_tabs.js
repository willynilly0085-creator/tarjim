// The settings page's tabs (2026-11-09): a tab list the keyboard can walk with the arrow keys,
// in the page's own reading direction.
import { $ } from "./api.js";
import { t } from "./i18n.js";
import { button, el } from "./ui.js";
import { TABS } from "./prefs_words.js";

export function tabList(show, current) {
  const list = el("div", { className: "prefs-tabs" }, TABS.map((tab) => {
    const one = button(t(`tab_${tab.id}`), () => show(tab.id), "prefs-tab");
    one.id = `prefs-tab-${tab.id}`;
    one.dataset.tab = tab.id;
    one.setAttribute("role", "tab");
    one.setAttribute("aria-controls", "prefs-panel");
    return one;
  }));
  list.setAttribute("role", "tablist");
  list.addEventListener("keydown", (event) => {
    const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
    if (!step) return;
    const ahead = document.documentElement.dir === "rtl" ? -step : step;
    const at = TABS.findIndex((tab) => tab.id === current());
    const next = TABS[(at + ahead + TABS.length) % TABS.length].id;
    show(next);
    $(`prefs-tab-${next}`).focus();
  });
  return list;
}
