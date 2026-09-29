import { $, api, post } from "./api.js";
import { t } from "./i18n.js";
import { localPanel, modelNeeded } from "./local.js";
import { fillModels, modelOptions } from "./models.js";
import { signInPanel } from "./signin.js";

let view = null;

const method = () => document.querySelector("input[name=method]:checked")?.value || "api";
function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children.filter((child) => child !== ""));
  return node;
}

const keyed = (p) => "has_key" in p;

function listed() {
  if (method() === "local") return view.local.servers;
  if (method() === "subscription") return [...view.subscription, ...view.api.filter((p) => p.plan)];
  return view.api.filter((p) => !p.plan);
}

function options() {
  if (!view) return [];
  return listed().map((p) => ({ id: p.id, name: p.name, ready: method() === "local" || p.ready, keyed: "has_key" in p }));
}

function current() {
  return listed().find((p) => p.id === $("connect-provider").value);
}

const OTHER = "__other";
function suggest(models, picked, source = {}) {
  const list = picked && !models.includes(picked) ? [...models, picked] : models;
  const chosen = picked || source.suggested || list[0] || "";
  fillModels($("connect-model-pick"), modelOptions(source, list), chosen, [new Option(t("modelOther"), OTHER, false, !list.length)]);
  $("connect-model").value = chosen;
  $("connect-model").hidden = list.length > 0;
}

function pickModel() {
  const other = $("connect-model-pick").value === OTHER;
  $("connect-model").hidden = !other;
  $("connect-model").value = other ? "" : $("connect-model-pick").value;
  if (other) $("connect-model").focus();
}

async function keyForm(provider) {
  const input = el("input", { className: "text-input", type: "password", dir: "ltr", autocomplete: "off",
    spellcheck: false, placeholder: provider.has_key ? t("keySet") : "" });
  const note = el("span", { className: "meta key-state", role: "status" });
  const save = el("button", { type: "submit", className: "button-quiet", textContent: t("keySave") });
  const form = el("form", { className: "key-row", noValidate: true },
    el("label", { className: "field" }, el("span", { className: "field-label", textContent: t("keyLabel") }), input),
    el("div", { className: "row" }, provider.key_url ? el("a", { className: "text-link", href: provider.key_url,
      target: "_blank", rel: "noopener noreferrer", textContent: t("getKey") }) : "", save, note));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    note.textContent = t("keyChecking");
    try {
      await post("/keys", { provider: provider.id, key: input.value.trim() });
      input.value = "";
      note.textContent = t("keySaved");
      await refresh(provider.id);
    } catch (error) {
      note.textContent = t(error.body?.result === "rejected" ? "keyRejected" : "keyShape");
    }
  });
  return form;
}

function addressForm(provider) {
  const input = el("input", { className: "text-input", type: "url", dir: "ltr", value: provider.base_url || "",
    placeholder: "https://example.com/v1" });
  const form = el("form", { className: "row", noValidate: true },
    el("label", { className: "field grow" }, el("span", { className: "field-label", textContent: t("addressLabel") }), input),
    el("button", { type: "submit", className: "button-quiet", textContent: t("keySave") }));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await post("/connections/address", { url: input.value.trim() }).catch(() => null);
  });
  return form;
}

function subscriptionDetail(provider) {
  if (!provider.ready) {
    return [el("p", { className: "meta", textContent: t("subscriptionInstall") }),
      el("code", { className: "command", dir: "ltr", textContent: provider.install }),
      el("button", { type: "button", className: "button-quiet", textContent: t("checkAgain"),
        onclick: () => refresh(provider.id) })];
  }
  return [signInPanel(provider)];
}

async function detail() {
  fillListeners();
  const provider = current();
  const box = $("connect-detail");
  $("connect-model-field").hidden = !provider;
  if (!provider) {
    box.replaceChildren(...(method() === "local" ? localPanel(view.local, refresh) : [el("p", { className: "meta", textContent: t("none") })]));
    return;
  }
  if (method() === "local") {
    box.replaceChildren(el("p", { className: "meta", dir: "ltr", textContent: provider.url }),
      ...(provider.models.length ? [] : [modelNeeded(provider)]), ...localPanel(view.local, refresh));
    suggest(provider.models, view.local.server === provider.id ? view.local.model : "");
  } else if (method() === "subscription" && !keyed(provider)) {
    box.replaceChildren(...subscriptionDetail(provider));
    suggest(provider.models, provider.model, provider);
  } else {
    const terms = provider.plan ? [el("p", { className: "meta", textContent: t(`planTerms_${provider.id}`) })] : [];
    box.replaceChildren(...(provider.id === "custom" ? [addressForm(provider)] : []), await keyForm(provider), ...terms);
    const listed = provider.has_key ? await post("/connections/models", { provider: provider.id }).catch(() => ({})) : {};
    suggest(listed.models || [], provider.model, listed);
  }
}

function listenLabel(way) {
  if (way.id !== "local") return way.ready ? way.name : `${way.name} · ${t("needsKey")}`;
  return way.ready ? t("listenLocalName") : `${t("listenLocalName")} · ${t("needsDownload", { gb: way.download_gb })}`;
}

function fillListeners() {
  const picked = $("connect-listen").value || view.chosen.listen;
  $("connect-listen").replaceChildren(...view.listening.map((way) => Object.assign(
    new Option(listenLabel(way), way.id, false, way.id === picked), { disabled: way.id !== "local" && !way.ready })));
  const local = view.listening.find((way) => way.id === "local");
  $("listen-hint").textContent = t(local.gpu ? "reason_gpu" : "reason_cpu_slow");
}

function fillProviders(picked) {
  const list = options();
  $("connect-provider").replaceChildren(...list.map((p) =>
    new Option(p.ready ? p.name : `${p.name} · ${t(p.keyed ? "needsKey" : "notInstalled")}`, p.id, false, p.id === picked)));
  $("connect-provider").closest(".field").hidden = list.length === 0;
  return detail();
}

async function refresh(picked, fresh) {
  view = fresh || await api("/connections");
  await fillProviders(picked || $("connect-provider").value);
}

function methodOf(provider) {
  if (provider === "local") return "local";
  const plan = view.api.some((p) => p.id === provider && p.plan);
  return plan || view.subscription.some((p) => p.id === provider) ? "subscription" : "api";
}

export async function renderConnect() {
  view = await api("/connections");
  const translate = view.chosen.translate;
  document.querySelector(`input[name=method][value=${methodOf(translate)}]`).checked = true;
  await fillProviders(translate === "local" ? view.local.server : translate);
}

export async function saveConnect() {
  const provider = current();
  if (!provider || provider.ready === false) return "connectNotReady";
  const local = method() === "local";
  const body = { provider: local ? "local" : provider.id, model: $("connect-model").value.trim(),
    listen: $("connect-listen").value, ...(local ? { server: provider.id } : {}) };
  try {
    await post("/connections/use", body);
  } catch {
    return "connectNotReady";
  }
  return "";
}

export function wireConnect() {
  document.querySelectorAll("input[name=method]").forEach((input) => input.addEventListener("change", () => fillProviders("")));
  $("connect-provider").addEventListener("change", detail);
  $("connect-model-pick").addEventListener("change", pickModel);
}
