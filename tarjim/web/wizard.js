import { $, post } from "./api.js";
import { load, t } from "./i18n.js";
import { renderChat } from "./chat.js";
import { renderConnect, saveConnect, wireConnect } from "./connect.js";
import { fillLanguageChoices } from "./languages.js";
import { copyText, selectText } from "./ui.js";
import { renderPhone } from "./phone.js";
import { renderDevice, renderTools } from "./steps.js";

const STEPS = ["language", "device", "connect", "tools", "extension", "chat", "done"];
let at = 0;
let poll = 0;
let state;
let finish;

const ENTER = {
  language: () => fillLanguageChoices(state.setup.ui_languages, document.documentElement.lang),
  device: () => renderDevice(state),
  connect: () => renderConnect(),
  tools: () => watchTools(),
  extension: () => {
    $("extension-path").textContent = state.setup.extension_path;
    $("copy-path").textContent = t("copy");
  },
  chat: () => renderChat(),
};

const LEAVE = {
  language: async () => {
    const language = document.querySelector("input[name=ui]:checked")?.value;
    if (language) state.setup = await post("/setup", { ui_language: language });
    if (language) await load(language);
    $("ui-language").value = document.documentElement.lang;
  },
  connect: () => saveConnect(),
  tools: () => (state.tools?.every((tool) => !tool.required || tool.installed) ? "" : "requiredMissing"),
  done: async () => { await post("/setup", { setup_done: "yes" }); finish(); },
};

async function watchTools() {
  clearInterval(poll);
  if (await renderTools(state, watchTools)) poll = setInterval(async () => {
    if (!(await renderTools(state, watchTools))) clearInterval(poll);
  }, 2000);
}

function paint() {
  document.querySelectorAll(".step").forEach((el) => el.classList.toggle("current", el.dataset.step === STEPS[at]));
  $("step-count").textContent = t("stepOf", { n: at + 1, total: STEPS.length });
  $("step-track").replaceChildren(...STEPS.map((_, i) =>
    Object.assign(document.createElement("li"), { className: i < at ? "past" : i === at ? "now" : "" })));
  $("step-back").hidden = at === 0;
  $("step-next").textContent = t(at === STEPS.length - 1 ? "start" : "next");
  $("step-error").hidden = true;
  ENTER[STEPS[at]]?.();
}

async function next() {
  const problem = await LEAVE[STEPS[at]]?.();
  if (problem) {
    $("step-error").textContent = t(problem);
    $("step-error").hidden = false;
    return;
  }
  if (at < STEPS.length - 1) at += 1;
  clearInterval(poll);
  paint();
}

export function startWizard(setup, onFinish, from = "language") {
  state = { setup };
  $("wizard").classList.remove("settings");
  $("settings-bar").hidden = true;
  finish = onFinish;
  at = Math.max(0, STEPS.indexOf(from));
  $("workspace").hidden = true;
  $("assistant").hidden = true;
  $("wizard").hidden = false;
  paint();
}

export function wireWizard() {
  $("step-next").addEventListener("click", next);
  $("step-back").addEventListener("click", () => { at = Math.max(0, at - 1); clearInterval(poll); paint(); });
  wireConnect();
  $("copy-path").addEventListener("click", async () => {
    const path = $("extension-path");
    if (await copyText(path.textContent)) $("copy-path").textContent = t("copied");
    else selectText(path);
  });
}

export const repaint = () => {
  if ($("wizard").hidden) return;
  if ($("wizard").classList.contains("settings")) showAll();
  else paint();
};

function showAll() {
  document.querySelectorAll(".step").forEach((el) => el.classList.toggle("current", el.dataset.step !== "done"));
  STEPS.filter((step) => step !== "done").forEach((step) => ENTER[step]?.());
  renderPhone();
}

async function saveAll() {
  $("settings-note").textContent = "";
  await LEAVE.language();
  const problem = await saveConnect();
  $("settings-note").textContent = t(problem || "saved");
}

export function startSettings(setup, onClose, onRescan) {
  state = { setup };
  $("workspace").hidden = true;
  $("assistant").hidden = true;
  $("wizard").hidden = false;
  $("wizard").classList.add("settings");
  $("settings-bar").hidden = false;
  $("settings-save").onclick = saveAll;
  $("settings-close").onclick = () => { $("wizard").classList.remove("settings"); $("settings-bar").hidden = true; onClose(); };
  $("settings-rescan").onclick = () => { $("wizard").classList.remove("settings"); $("settings-bar").hidden = true; onRescan(); };
  showAll();
}
