import { $, post } from "./api.js";
import { load, t } from "./i18n.js";
import { engineChoice, neededKeys, renderDevice, renderEngine, renderKeys, renderTools } from "./steps.js";

const STEPS = ["language", "device", "engine", "keys", "tools", "extension", "done"];
let at = 0;
let poll = 0;
let state;
let finish;

const ENTER = {
  language: () => {
    const input = document.querySelector(`input[name=ui][value=${document.documentElement.lang}]`);
    if (input) input.checked = true;
  },
  device: () => renderDevice(state),
  engine: () => renderEngine(state),
  keys: () => renderKeys(state),
  tools: () => watchTools(),
  extension: () => { $("extension-path").textContent = state.setup.extension_path; },
};

const LEAVE = {
  language: async () => {
    const language = document.querySelector("input[name=ui]:checked")?.value;
    if (language) state.setup = await post("/setup", { ui_language: language });
    if (language) await load(language);
    $("ui-language").value = document.documentElement.lang;
  },
  engine: async () => { state.setup = { ...state.setup, ...(await post("/setup", engineChoice())) }; },
  keys: () => (neededKeys(state).every((p) => state.setup.keys[p]) ? "" : "keysMissing"),
  tools: () => (state.tools?.every((tool) => !tool.required || tool.installed) ? "" : "requiredMissing"),
  done: async () => { await post("/setup", { setup_done: "yes" }); finish(); },
};

async function watchTools() {
  clearInterval(poll);
  if (await renderTools(state)) poll = setInterval(async () => {
    if (!(await renderTools(state))) clearInterval(poll);
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
  finish = onFinish;
  at = Math.max(0, STEPS.indexOf(from));
  $("workspace").hidden = true;
  $("wizard").hidden = false;
  paint();
}

export function wireWizard() {
  $("step-next").addEventListener("click", next);
  $("step-back").addEventListener("click", () => { at = Math.max(0, at - 1); clearInterval(poll); paint(); });
  document.querySelectorAll("input[name=engine]").forEach((el) => el.addEventListener("change", () => {
    $("advanced").hidden = el.value !== "advanced" || !el.checked;
  }));
  $("copy-path").addEventListener("click", async () => {
    await navigator.clipboard.writeText($("extension-path").textContent);
    $("copy-path").textContent = t("copied");
  });
}

export const repaint = () => { if (!$("wizard").hidden) paint(); };
