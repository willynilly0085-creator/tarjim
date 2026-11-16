// Who translates the text a person selects in the browser, apart from the videos' translator
// (engine.js, whose lists this shares). "Automatic" saves nothing: tarjim then asks the one
// that answers soonest. A picked translator starts on its suggested model, the lighter one,
// since a selection is waited for; the person can pick any other.
import { $, api, post } from "./api.js";
import { choices, lineText, modelsOf } from "./engine.js";
import { t } from "./i18n.js";
import { fillModels, modelOptions } from "./models.js";
import { problem } from "./problems.js";

const NONE = { provider: "", model: "", server: "", name: "", label: "" };
const state = { view: null, saved: NONE, wired: false };

const valueOf = (saved) => (saved.provider === "local" ? `local:${saved.server}` : saved.provider);
const picked = () => choices(state.view).find((c) => c.value === $("text-engine-provider").value);

function showNow() {
  const { provider, name, label } = state.saved;
  $("text-engine-now").textContent = provider ? lineText({ name, model: label }) : t("textEngineAuto");
}

async function fillModelList(choice) {
  const select = $("text-engine-model");
  const field = select.closest(".field");
  field.hidden = !choice;
  if (!choice) return "";
  select.disabled = true;
  select.replaceChildren(new Option(t("engineLoading"), ""));
  const source = await modelsOf(state.view, choice);
  if (picked()?.value !== choice.value) return null;  // another translator was picked meanwhile
  const mine = valueOf(state.saved) === choice.value ? state.saved.model : "";
  const chosen = mine || source.suggested || source.saved || source.models[0] || "";
  const list = chosen && !source.models.includes(chosen) ? [...source.models, chosen] : source.models;
  fillModels(select, modelOptions(source, list), chosen);
  select.disabled = list.length === 0;
  field.hidden = list.length === 0;  // the provider's own default
  return chosen;
}

// A saved translator that stopped working stays in the list, named as such.
function fillProviders() {
  const list = choices(state.view);
  const now = valueOf(state.saved);
  const stale = now && !list.some((c) => c.value === now);
  const extra = stale ? [new Option(t("engineBroken", { name: state.saved.name }), now, true, true)] : [];
  $("text-engine-provider").replaceChildren(new Option(t("textEngineAuto"), "", false, !now), ...extra,
    ...list.map((c) => new Option(c.name, c.value, false, c.value === now)));
}

async function save(model) {
  const choice = picked();
  const body = choice?.server ? { provider: "local", server: choice.server.id, model }
    : { provider: choice?.value || "", model };
  $("text-engine-note").textContent = t("engineSaving");
  try {
    state.saved = await post("/text/use", body);
    $("text-engine-note").textContent = t("textEngineSaved");
    showNow();
  } catch (error) {
    $("text-engine-note").textContent = problem(error, { unusable: "engineUnusable" });
  }
}

async function open() {
  if (!$("text-engine").open || state.view) return;
  $("text-engine-provider").replaceChildren(new Option(t("engineLoading"), ""));
  $("text-engine-model").closest(".field").hidden = true;
  $("text-engine-note").textContent = t("textEngineHint");
  state.view = await api("/connections").catch(() => null);
  if (!state.view) {
    $("text-engine-provider").replaceChildren();
    $("text-engine-note").textContent = t("engineLoadFailed");
    return;
  }
  fillProviders();
  await fillModelList(picked());
}

function wire() {
  $("text-engine").addEventListener("toggle", open);
  $("text-engine-provider").addEventListener("change", async () => {
    const model = await fillModelList(picked());
    if (model !== null) await save(model);
  });
  $("text-engine-model").addEventListener("change", () => save($("text-engine-model").value));
  state.wired = true;
}

export async function showTextEngine() {
  if (!state.wired) wire();
  state.view = null;
  $("text-engine").open = false;
  state.saved = await api("/text").catch(() => NONE);
  showNow();
}
