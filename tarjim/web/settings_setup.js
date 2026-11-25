// The setup's sections as settings (2026-11-25): one section at a time beside the settings list,
// under the same head as the settings page, instead of all eight down one long page. Each
// section is the setup's own, filled and saved as before; the bar shows "save" only where there
// is something to save (the AI link) and "check my device again" only on the device.
import { $ } from "./api.js";
import { t } from "./i18n.js";
import { button, el, showSection } from "./ui.js";
import { markCurrent, settingsNav } from "./settings_nav.js";

let shown = "device";
let go = () => {};

// The head and the list, in the page's language; returns the list.
function draw() {
  const back = button(t("back"), () => $("settings-close").click(), "button-quiet prefs-back");
  $("setup-head").replaceChildren(el("p", { className: "page-title", textContent: t("prefsTitle") }), back);
  const nav = settingsNav(() => shown, (id, key) => go(id, key), "setup");
  $("setup-side").replaceChildren(nav);
  markCurrent(nav, shown);
  return nav;
}

// open(id, byKey): what the list does when another tab or section is chosen (main.js).
export function showSetupSection(section, open, byKey = false) {
  shown = section;
  go = open;
  $("wizard").dataset.only = section;
  document.querySelectorAll("#wizard .step").forEach((step) => step.classList.toggle("only", step.dataset.step === section));
  const nav = draw();
  if (byKey) markCurrent(nav, section, true);
  else showSection(section);
}

// The page's language changed while a section is shown: the head and the list follow it.
export function repaintSetupSection() {
  if ($("wizard").hidden || !$("wizard").classList.contains("settings")) return;
  draw();
}
