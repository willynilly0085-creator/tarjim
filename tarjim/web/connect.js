import { $, api, post } from "./api.js";
import { t } from "./i18n.js";

let view = null;

const method = () => document.querySelector("input[name=method]:checked")?.value || "api";
function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children.filter((child) => child !== ""));
  return node;
}

function options() {
  if (method() === "local") return view.local.servers.map((s) => ({ id: s.id, name: s.name, ready: true }));
  return view[method()].map((p) => ({ id: p.id, name: p.name, ready: p.ready }));
}

function current() {
  const id = $("connect-provider").value;
  if (method() === "local") return view.local.servers.find((s) => s.id === id);
  return view[method()].find((p) => p.id === id);
}

function suggest(models, picked) {
  $("connect-models").replaceChildren(...models.map((m) => new Option(m, m)));
  $("connect-model").value = picked || models[0] || "";
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
  const signIn = el("button", { type: "button", className: "button-quiet", textContent: t("signIn") });
  signIn.addEventListener("click", () => post("/connections/sign-in", { provider: provider.id }));
  return [el("p", { className: "meta", textContent: t("subscriptionReady") }), signIn];
}

async function detail() {
  const provider = current();
  const box = $("connect-detail");
  $("connect-model-field").hidden = !provider;
  if (!provider) {
    box.replaceChildren(el("p", { className: "meta", textContent: t(method() === "local" ? "localNone" : "none") }));
    return;
  }
  if (method() === "local") {
    box.replaceChildren(el("p", { className: "meta", dir: "ltr", textContent: provider.url }));
    suggest(provider.models, view.local.server === provider.id ? view.local.model : "");
  } else if (method() === "subscription") {
    box.replaceChildren(...subscriptionDetail(provider));
    suggest(provider.models, provider.model);
  } else {
    box.replaceChildren(...(provider.id === "custom" ? [addressForm(provider)] : []), await keyForm(provider));
    const { models = [] } = provider.has_key ? await post("/connections/models", { provider: provider.id }) : {};
    suggest(models, provider.model);
  }
  $("connect-listen").textContent = t("listenWith", { name: listenerName(provider) });
}

function listenerName(provider) {
  if (method() === "api" && provider.hears && provider.ready) return provider.name;
  return view.api.find((p) => p.id === "gemini")?.ready ? "Google Gemini" : t("listenLocal");
}

function fillProviders(picked) {
  const list = options();
  $("connect-provider").replaceChildren(...list.map((p) =>
    new Option(p.ready ? p.name : `${p.name} · ${t(method() === "api" ? "needsKey" : "notInstalled")}`, p.id, false, p.id === picked)));
  $("connect-provider").closest(".field").hidden = list.length === 0;
  return detail();
}

async function refresh(picked) {
  view = await api("/connections");
  await fillProviders(picked || $("connect-provider").value);
}

function methodOf(provider) {
  if (provider === "local") return "local";
  return view.subscription.some((p) => p.id === provider) ? "subscription" : "api";
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
  const body = { provider: local ? "local" : provider.id, model: $("connect-model").value.trim(), ...(local ? { server: provider.id } : {}) };
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
}
