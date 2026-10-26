import { $, api, post } from "./api.js";
import { t } from "./i18n.js";
import { localPanel, modelNeeded } from "./local.js";
import { forgetKeyForm, keyForm, submitKey, typedKey } from "./keyform.js";
import { fillModels, modelOptions } from "./models.js";
import { signInPanel } from "./signin.js";

let view = null;
let preferred = "";  // a way to open on once, e.g. "api" for someone who said they have a key

export const preferKeys = () => { preferred = "api"; };

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
  return listed().map((p) => ({ id: p.id, name: p.name, ready: method() === "local" || p.ready, keyed: "has_key" in p,
    signedOut: p.signed_in === false && p.ready }));
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
  forgetKeyForm();
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
    box.replaceChildren(...(provider.id === "custom" ? [addressForm(provider)] : []), keyForm(provider, () => refresh(provider.id)), ...terms);
    const listed = provider.has_key ? await post("/connections/models", { provider: provider.id }).catch(() => ({})) : {};
    suggest(listed.models || [], provider.model, listed);
    if (!provider.has_key) box.append(el("p", { className: "meta", textContent: t("modelsAfterKey") }));
  }
}

function listenLabel(way) {
  if (way.id !== "local") return way.ready ? way.name : `${way.name} · ${t(way.sign_in ? "needsSignIn" : "needsKey")}`;
  return way.ready ? t("listenLocalName") : `${t("listenLocalName")} · ${t("needsDownload", { gb: way.download_gb })}`;
}

function fillListeners() {
  const picked = $("connect-listen").value || view.chosen.listen;
  $("connect-listen").replaceChildren(...view.listening.map((way) => Object.assign(
    new Option(listenLabel(way), way.id, false, way.id === picked), { disabled: way.id !== "local" && !way.ready })));
  listenHint();
}

// The words under the listening choice describe the one picked, not always the local model.
function listenHint() {
  const local = view.listening.find((way) => way.id === "local");
  const onComputer = $("connect-listen").value === "local";
  $("listen-hint").textContent = onComputer ? t(local.gpu ? "reason_gpu" : "reason_cpu_slow") : "";
}

function fillProviders(picked) {
  const list = options();
  $("connect-provider").replaceChildren(...list.map((p) =>
    new Option(p.signedOut ? `${p.name} · ${t("needsSignIn")}` : p.ready ? p.name : `${p.name} · ${t(p.keyed ? "needsKey" : "notInstalled")}`,
      p.id, false, p.id === picked)));
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
  const way = preferred || methodOf(translate);
  preferred = "";
  document.querySelector(`input[name=method][value=${way}]`).checked = true;
  await fillProviders(translate === "local" ? view.local.server : translate);
}

export async function saveConnect() {
  const provider = current();
  const typed = typedKey();
  if (provider && typed) {  // a key pasted then saved with the big button, not the small one
    const problem = await submitKey(provider, typed);
    if (problem) return problem;
    await refresh(provider.id);
  }
  if (!current() || current().ready === false) return "connectNotReady";
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
  $("connect-listen").addEventListener("change", listenHint);
}
