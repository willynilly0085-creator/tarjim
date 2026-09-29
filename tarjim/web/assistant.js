import { api, post } from "./api.js";
import { t } from "./i18n.js";
import { aiScreen } from "./assistant_ai.js";
import { planScreen } from "./assistant_plan.js";
import { progressScreen, readyScreen } from "./assistant_finish.js";
import { scanScreen } from "./assistant_scan.js";
import { el } from "./ui.js";

const flow = { finish: null, manual: null };

function screen(...children) {
  const main = document.getElementById("assistant");
  main.replaceChildren(el("section", { className: "screen" }, ...children));
  main.querySelector("h1")?.focus({ preventScroll: true });
  window.scrollTo({ top: 0 });
}

function pathChoice(id, recommended, onPick) {
  const title = el("span", { className: "path-title", textContent: t(`path_${id}`) },
    recommended ? el("em", { className: "tag", textContent: t("recommended") }) : "");
  return el("button", { type: "button", className: `path${recommended ? " recommended" : ""}`, onclick: onPick },
    title, el("span", { className: "path-hint", textContent: t(`path_${id}_hint`) }));
}

function welcome() {
  screen(el("h1", { tabIndex: -1, textContent: t("welcomeTitle") }),
    el("p", { className: "lede", textContent: t("welcomeHint") }),
    el("div", { className: "paths" },
      pathChoice("auto", true, scan),
      pathChoice("ai", false, ai),
      pathChoice("manual", false, () => flow.manual("language"))),
    el("p", { className: "meta privacy", textContent: t("welcomePrivacy") }));
}

async function scan() {
  await scanScreen(screen);
  const [{ plan, scan: found }, view] = await Promise.all([api("/setup/plan"), api("/connections")]);
  const apiModels = Object.fromEntries(await Promise.all(found.keys.saved.map(async (provider) =>
    [provider, await post("/connections/models", { provider }).catch(() => ({ models: [] }))])));
  planScreen(screen, { plan, scan: found, view, apiModels }, { back: welcome, apply: progress, manual: flow.manual });
}

function ai() {
  aiScreen(screen, { back: welcome, done: scan });
}

function progress(started) {
  progressScreen(screen, started, () => readyScreen(screen, flow.finish, () => flow.manual("extension")));
}

export function startAssistant(onFinish, onManual) {
  flow.finish = onFinish;
  flow.manual = onManual;
  document.getElementById("workspace").hidden = true;
  document.getElementById("wizard").hidden = true;
  document.getElementById("assistant").hidden = false;
  welcome();
}

export function repaintAssistant() {
  if (!document.getElementById("assistant").hidden) welcome();
}
