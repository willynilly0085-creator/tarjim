// The translator and its model, changed in place next to Translate. Only translators that work
// right now are offered: a saved key, a subscription app that is signed in, a local AI running.
// The line shows the saved choice at once; the lists load only when the person opens it.
import { $, api, post } from "./api.js";
import { t } from "./i18n.js";
import { fillModels, modelOptions } from "./models.js";

const state = { view: null, wired: false };

function choices(view) {
  const apps = view.subscription.filter((p) => p.ready && p.signed_in);
  const keyed = view.api.filter((p) => p.ready);
  return [...apps, ...keyed].map((p) => ({ value: p.id, name: p.name, entry: p }))
    .concat(view.local.servers.map((s) => ({ value: `local:${s.id}`, name: s.name, server: s })));
}

function currentValue(view) {
  const translate = view.chosen.translate;
  return translate === "local" ? `local:${view.local.server}` : translate;
}

const picked = () => choices(state.view).find((c) => c.value === $("engine-provider").value);

async function modelsOf(choice) {
  if (choice.server) {
    const mine = state.view.local.server === choice.server.id;
    return { models: choice.server.models, saved: mine ? state.view.local.model : "" };
  }
  if ("models" in choice.entry) return { ...choice.entry, saved: choice.entry.model };
  const listed = await post("/connections/models", { provider: choice.value }).catch(() => ({}));
  return { ...listed, models: listed.models || [], saved: choice.entry.model };
}

async function fillModelList(choice) {
  const select = $("engine-model");
  select.disabled = true;
  select.closest(".field").hidden = false;
  select.replaceChildren(new Option(t("engineLoading"), ""));
  const source = await modelsOf(choice);
  const chosen = source.saved || source.suggested || source.models[0] || "";
  const list = chosen && !source.models.includes(chosen) ? [...source.models, chosen] : source.models;
  fillModels(select, modelOptions(source, list), chosen);
  select.disabled = list.length === 0;
  select.closest(".field").hidden = list.length === 0;  // the provider's own default
  return chosen;
}

function fillProviders() {
  const list = choices(state.view);
  const now = currentValue(state.view);
  const known = list.some((c) => c.value === now);
  const extra = known ? [] : [new Option($("engine-now").textContent, now, true, true)];
  $("engine-provider").replaceChildren(...extra, ...list.map((c) => new Option(c.name, c.value, false, c.value === now)));
  $("engine-note").textContent = list.length > 1 ? "" : t("engineNone");
  return known ? picked() : null;
}

// "Claude · Opus 5.5", not "Claude · Claude Opus 5.5".
function lineText(now) {
  const model = now.model.startsWith(`${now.name} `) ? now.model.slice(now.name.length + 1) : now.model;
  return model ? `${now.name} · ${model}` : now.name;
}

async function showNow() {
  const now = await api("/connections/current").catch(() => null);
  if (now) $("engine-now").textContent = lineText(now);
}

async function save(model) {
  const choice = picked();
  const local = Boolean(choice.server);
  const body = { provider: local ? "local" : choice.value, model, listen: state.view.chosen.listen,
    ...(local ? { server: choice.server.id } : {}) };
  $("engine-note").textContent = t("engineSaving");
  try {
    state.view = await post("/connections/use", body);
    $("engine-note").textContent = t("engineSaved");
    await showNow();
  } catch {
    $("engine-note").textContent = t("engineFailed");
  }
}

async function open() {
  if (!$("engine").open || state.view) return;
  $("engine-provider").replaceChildren(new Option(t("engineLoading"), ""));
  $("engine-model").closest(".field").hidden = true;
  state.view = await api("/connections").catch(() => null);
  if (!state.view) {
    $("engine-provider").replaceChildren();
    $("engine-note").textContent = t("engineFailed");
    return;
  }
  const choice = fillProviders();
  if (choice) await fillModelList(choice);
  else $("engine-model").replaceChildren();
}

function wire() {
  $("engine").addEventListener("toggle", open);
  $("engine-provider").addEventListener("change", async () => {
    const choice = picked();
    if (choice) await save(await fillModelList(choice));
  });
  $("engine-model").addEventListener("change", () => save($("engine-model").value));
  state.wired = true;
}

export async function showEngine() {
  if (!state.wired) wire();
  state.view = null;
  $("engine").open = false;
  await showNow();
}
