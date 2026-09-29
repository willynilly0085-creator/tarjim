import { post } from "./api.js";
import { t } from "./i18n.js";

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children.filter((child) => child !== ""));
  return node;
}

function installedRow(program, refresh) {
  const note = el("span", { className: "meta", role: "status" });
  const models = program.models.length ? t("localModels", { list: new Intl.ListFormat(document.documentElement.lang).format(program.models) }) : "";
  const row = el("div", { className: "local-program" },
    el("p", { className: "choice-name", textContent: t("localInstalled", { name: program.name }) }),
    models ? el("p", { className: "meta", dir: "auto", textContent: models }) : "");
  if (!program.can_start) {
    row.append(el("p", { className: "meta", textContent: t("localNoStart", { name: program.name }) }));
    return row;
  }
  const start = el("button", { type: "button", className: "primary compact", textContent: t("localStart") });
  start.addEventListener("click", async () => {
    start.disabled = true;
    note.textContent = t("localStarting");
    const reply = await post("/connections/start-local", { server: program.id }).catch(() => null);
    if (reply?.started) await refresh(program.id, reply);
    else { note.textContent = t("localStartFailed"); start.disabled = false; }
  });
  row.append(el("div", { className: "row" }, start, note));
  return row;
}

function pathForm(refresh) {
  const input = el("input", { className: "text-input", dir: "ltr", autocomplete: "off", spellcheck: false,
    placeholder: "C:\\Users\\...\\ollama.exe" });
  const note = el("span", { className: "meta", role: "status" });
  const form = el("form", { className: "key-row", noValidate: true },
    el("label", { className: "field" }, el("span", { className: "field-label", textContent: t("localPathLabel") }), input),
    el("div", { className: "row" }, el("button", { type: "submit", className: "button-quiet", textContent: t("localPathSave") }), note));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const reply = await post("/connections/local-program", { path: input.value }).catch(() => null);
    if (reply?.server) await refresh(reply.server, reply);
    else note.textContent = t("localPathBad");
  });
  return form;
}

function searchPart(refresh) {
  const note = el("p", { className: "meta", role: "status", textContent: t("localSearchHint") });
  const button = el("button", { type: "button", className: "button-quiet", textContent: t("localSearch") });
  const box = el("div", { className: "local-search" }, note, button);
  button.addEventListener("click", async () => {
    button.disabled = true;
    note.textContent = t("localSearching");
    const reply = await post("/connections/scan-local", {}).catch(() => null);
    button.disabled = false;
    if (reply?.found?.length) await refresh("", reply);
    else box.replaceChildren(el("p", { className: "meta", textContent: t("localSearchNone") }), pathForm(refresh));
  });
  return box;
}

export function localPanel(local, refresh) {
  const parts = local.installed.map((program) => installedRow(program, refresh));
  if (!local.servers.length) parts.unshift(el("p", { className: "meta", textContent: t("localNone") }));
  return [...parts, searchPart(refresh)];
}

export function modelNeeded(program) {
  const row = el("div", { className: "local-program" },
    el("p", { className: "choice-name", textContent: t("localNoModel", { name: program.name }) }));
  if (program.id !== "ollama") {
    row.append(el("p", { className: "meta", textContent: t("localNoModelOther", { name: program.name }) }));
    return row;
  }
  const note = el("span", { className: "meta", role: "status" });
  const get = el("button", { type: "button", className: "primary compact", textContent: t("localGetModel") });
  get.addEventListener("click", async () => {
    get.disabled = true;
    const reply = await post("/tools/local_translation", {}).catch(() => null);
    note.textContent = t(reply ? "localModelDownloading" : "localStartFailed");
    if (!reply) get.disabled = false;
  });
  row.append(el("p", { className: "meta", textContent: t("localModelHint") }), el("div", { className: "row" }, get, note));
  return row;
}
