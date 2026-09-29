import { post } from "./api.js";
import { t } from "./i18n.js";
import { keyNeed } from "./assistant_key.js";
import { listenOptions, translateOptions } from "./assistant_options.js";
import { fillModels, modelOptions } from "./models.js";
import { button, el, status } from "./ui.js";

function downloads(state) {
  const installed = state.scan.tools.installed;
  const wanted = ["ffmpeg", "timing", ...(state.plan.listen.provider === "local" ? ["accuracy"] : [])];
  return wanted.filter((id) => !installed[id]);
}

function sizeOf(state, ids) {
  return Math.round(ids.reduce((sum, id) => sum + state.scan.tools.sizes[id], 0) * 10) / 10;
}

function choiceRow(label, options, picked, onPick) {
  const select = el("select", { className: "select" },
    ...options.map((o) => Object.assign(new Option(o.label, o.value, false, o.value === picked), { disabled: o.disabled })));
  const reason = el("p", { className: "meta" });
  const show = () => { reason.textContent = options.find((o) => o.value === select.value)?.why || ""; };
  select.addEventListener("change", () => { show(); onPick(options.find((o) => o.value === select.value)); });
  show();
  return el("div", { className: "plan-row" }, el("label", { className: "field" },
    el("span", { className: "field-label", textContent: label }), select), reason);
}

function modelSource(state) {
  const choice = state.plan.translate;
  if (choice.provider === "local") {
    return { models: state.scan.local.programs.find((p) => p.id === choice.server)?.models || [] };
  }
  return state.apiModels?.[choice.provider] || state.view.subscription.find((s) => s.id === choice.provider) || { models: [] };
}

function modelRow(state) {
  const source = modelSource(state);
  const options = modelOptions(source, source.models);
  if (!options.length) return "";
  const choice = state.plan.translate;
  if (!options.some((o) => o.value === choice.model)) choice.model = source.suggested || options[0].value;
  const select = el("select", { className: "select" });
  fillModels(select, options, choice.model);
  select.addEventListener("change", () => { choice.model = select.value; });
  return el("div", { className: "plan-row" }, el("label", { className: "field" },
    el("span", { className: "field-label", textContent: t("modelLabel") }), select),
    el("p", { className: "meta", textContent: t("modelWhy") }));
}

function downloadPart(state) {
  const ids = downloads(state);
  const total = sizeOf(state, ids);
  const low = state.scan.device.disk_free_gb < total + 2;
  return el("div", { className: "plan-row" },
    el("p", { className: "field-label", textContent: t("planDownloads") }),
    ids.length ? el("ul", { className: "plain" }, ...ids.map((id) =>
      el("li", {}, el("span", { textContent: t("planTool", { name: t(`tool_${id}`), gb: state.scan.tools.sizes[id] }) }),
        el("span", { className: "meta why", textContent: t(`tool_${id}_hint`) }))))
      : el("p", { className: "meta", textContent: t("planNothingToDownload") }),
    ids.length ? el("p", { className: "meta", textContent: t("planTotal", { gb: total, disk: state.scan.device.disk_free_gb }) }) : "",
    low ? el("p", { className: "error", textContent: t("planDiskLow") }) : "");
}

function needsKey(state) {
  const plan = state.plan;
  return [plan.translate, plan.listen].some((c) => ["gemini", "openai"].includes(c.provider) && !c.ready);
}

export function planScreen(screen, state, { back, apply, manual }) {
  const note = status();
  const start = button(t("planStart"), async () => {
    start.disabled = true;
    note.textContent = t("planApplying");
    const body = { translate: state.plan.translate, listen: state.plan.listen, downloads: downloads(state) };
    const reply = await post("/setup/apply", body).catch(() => null);
    if (reply?.saved) apply(reply.downloads);
    else { note.textContent = t("planApplyFailed"); start.disabled = false; }
  }, "primary");
  const paint = () => {
    const keyPart = needsKey(state) ? keyNeed(state, paint) : "";
    start.disabled = Boolean(keyPart);
    screen(el("h1", { tabIndex: -1, textContent: t("planTitle") }),
      el("p", { className: "lede", textContent: t("planHint") }),
      choiceRow(t("planTranslate"), translateOptions(state.scan), state.plan.translate.value || "",
        (o) => { if (o.value === "other") manual("connect"); else { state.plan.translate = o.choice; paint(); } }),
      modelRow(state),
      choiceRow(t("planListen"), listenOptions(state.scan), state.plan.listen.provider,
        (o) => { state.plan.listen = o.choice; paint(); }),
      downloadPart(state), keyPart,
      el("nav", { className: "step-nav" }, button(t("back"), back), start), note);
  };
  state.plan.translate.value = translateOptions(state.scan).find((o) => o.matches(state.plan.translate))?.value;
  paint();
}
