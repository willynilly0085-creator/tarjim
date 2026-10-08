import { $, api, post } from "./api.js";
import { t } from "./i18n.js";
import { button, el, wait } from "./ui.js";

const BACK_TRIES = 240;

async function waitForNewEngine(before) {
  for (let i = 0; i < BACK_TRIES; i += 1) {
    await wait(3000);
    const now = await api("/update").catch(() => null);
    if (now && now.current !== before) return location.reload();
    if (now?.failed) return false;
  }
  return false;
}

async function apply(state, box) {
  box.replaceChildren(el("span", { textContent: t("updating") }));
  const reply = await post("/update/apply", {}).catch((error) => error.body || {});
  if (reply.error === "busy") return box.replaceChildren(el("span", { textContent: t("updateBusy") }));
  if (!reply.started || (await waitForNewEngine(state.current)) === false) {
    box.replaceChildren(el("span", { textContent: t("updateFailed") }));
  }
}

export async function showUpdate() {
  const state = await api("/update").catch(() => null);
  const box = $("update-banner");
  box.hidden = !state?.available;
  if (box.hidden) return;
  const words = el("span", { textContent: t("updateAvailable", { version: state.latest }) });
  box.replaceChildren(words, state.can_install ? button(t("updateNow"), () => apply(state, box), "primary small")
    : el("span", { className: "meta", textContent: t("updateManual") }));
}

export function fillUpdateChoice(setup) {
  $("auto-update").checked = setup.auto_update !== false;
  $("auto-update").onchange = () => post("/setup", { auto_update: $("auto-update").checked });
  api("/update").then((state) => { $("version-line").textContent = t("versionLine", { version: state.current }); }).catch(() => {});
}
