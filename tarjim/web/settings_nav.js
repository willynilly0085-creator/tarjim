// One settings place (2026-11-25): the settings tabs and the setup's sections share one list,
// in three named groups, beside whichever is open. A setup section still saves through the
// setup's own bar; only where it is shown changed. Wide screens see a side list, narrow ones a
// row that scrolls; the arrow keys walk it in the page's reading direction.
import { t } from "./i18n.js";
import { button, el } from "./ui.js";

export const NAV = [
  { id: "video", items: ["look", "timing"] },
  { id: "work", items: ["listen", "translate", "output", "dub"] },
  { id: "app", items: ["general", "device", "connect", "tools", "voice", "extension", "chat", "phone"] },
];

const SETUP = new Set(["device", "connect", "tools", "voice", "extension", "chat", "phone"]);
const ORDER = NAV.flatMap((group) => group.items);

export const isSetup = (id) => SETUP.has(id);
export const navName = (id) => t(isSetup(id) ? `nav_${id}` : `tab_${id}`);

function item(id, current, go) {
  const one = button(navName(id), () => go(id), "prefs-tab");
  one.dataset.tab = id;
  one.setAttribute("aria-current", id === current ? "page" : "false");
  return el("li", {}, one);
}

function walk(event, current, go) {
  const forward = document.documentElement.dir === "rtl" ? "ArrowLeft" : "ArrowRight";
  const back = forward === "ArrowLeft" ? "ArrowRight" : "ArrowLeft";
  const step = { ArrowDown: 1, ArrowUp: -1, [forward]: 1, [back]: -1 }[event.key];
  if (!step) return;
  event.preventDefault?.();
  const at = ORDER.indexOf(current());
  go(ORDER[(at + step + ORDER.length) % ORDER.length], true);
}

// go(id, byKey): open that tab or section; current(): the one open now. Both pages hold a list
// at once, so ids carry the page's own prefix.
export function settingsNav(current, go, prefix) {
  const groups = NAV.map((group) => {
    const title = el("p", { className: "nav-group-title", id: `${prefix}-group-${group.id}`, textContent: t(`navGroup_${group.id}`) });
    const list = el("ul", {}, group.items.map((id) => item(id, current(), go)));
    list.setAttribute("aria-labelledby", title.id);
    return el("div", { className: "nav-group" }, title, list);
  });
  const nav = el("nav", { className: "settings-nav" }, groups);
  nav.setAttribute("aria-label", t("prefsTitle"));
  nav.addEventListener("keydown", (event) => walk(event, current, go));
  return nav;
}

// The list's mark follows the tab or section shown, and the shown one is scrolled into view.
export function markCurrent(nav, id, focus = false) {
  nav.querySelectorAll(".prefs-tab").forEach((one) => {
    one.setAttribute("aria-current", one.dataset.tab === id ? "page" : "false");
  });
  const shown = nav.querySelector(`.prefs-tab[data-tab="${id}"]`);
  shown?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
  if (focus) shown?.focus();
}
