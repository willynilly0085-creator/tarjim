import { api, post } from "./api.js";
import { t } from "./i18n.js";
import { signInPanel } from "./signin.js";
import { button, el, status, wait } from "./ui.js";

const INSTALL_POLL_MS = 4000;
const INSTALL_ROUNDS = 150;

// A failed install shows what the installer itself said, and can be tried again.
function failure(row, detail) {
  row.sub.installing = false;
  row.body.replaceChildren(status(t("aiInstallFailed"), "error"),
    detail ? el("p", { className: "job-error", dir: "ltr", textContent: detail }) : "",
    button(t("aiInstall"), () => install(row)));
}

async function follow(row) {
  for (let round = 0; round < INSTALL_ROUNDS && row.body.isConnected; round += 1) {
    await wait(INSTALL_POLL_MS);
    const now = (await api("/connections").catch(() => null))?.subscription.find((s) => s.id === row.sub.id);
    if (now?.install_failed) return failure(row, now.install_detail);
    if (now?.ready) {
      Object.assign(row.sub, now);
      row.app.installed = true;
      return row.installed();
    }
  }
  return row.body.isConnected ? failure(row, "") : null;
}

async function install(row) {
  row.sub.installing = true;
  row.body.replaceChildren(status(t("aiInstalling")));
  const reply = await post("/connections/install-app", { provider: row.sub.id }).catch(() => null);
  return reply ? follow(row) : failure(row, "");
}

function action(row) {
  const { app, sub } = row;
  if (app.signed_in) return [button(t("aiUse"), row.done, "primary compact")];
  if (app.installed || sub.ready) return [signInPanel(sub, row.done)];
  if (sub.installing) { follow(row); return [status(t("aiInstalling"))]; }
  if (sub.can_install) return [button(t("aiInstall"), () => install(row))];
  const site = sub.install.startsWith("http");
  return [status(t(site ? "aiFromSite" : "aiNeedsNode")), el("a", { className: "text-link", href: site ? sub.install : "https://nodejs.org/",
    target: "_blank", rel: "noopener noreferrer", textContent: t(site ? "aiOpenSite" : "aiGetNode") })];
}

// Whatever this subscription still needs, in one place: install its program, then sign in.
export function connectBody(app, sub, done, installed) {
  const row = { app, sub, done, body: el("div", { className: "ai-body" }) };
  row.installed = installed || (() => row.body.replaceChildren(signInPanel(sub, done)));
  row.body.append(...action(row).filter(Boolean));
  return row.body;
}

function appRow(app, sub, done) {
  const state = app.signed_in ? "aiSignedIn" : app.installed ? "aiInstalled" : "aiMissing";
  const body = connectBody(app, sub, done);
  return el("li", { className: "ai-app" },
    el("div", {}, el("p", { className: "choice-name", textContent: app.name }), el("p", { className: "meta", textContent: t(state) })),
    body);
}

function planRow(plan, done) {
  const input = el("input", { className: "text-input", type: "password", dir: "ltr", autocomplete: "off", spellcheck: false });
  const note = status();
  const form = el("form", { className: "ai-body", noValidate: true }, input,
    el("a", { className: "text-link", href: plan.key_url, target: "_blank", rel: "noopener noreferrer", textContent: t("getKeyFree") }),
    el("button", { type: "submit", className: "button-quiet", textContent: t("keySave") }), note);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    note.textContent = t("keyChecking");
    try {
      await post("/keys", { provider: plan.id, key: input.value.trim() });
      done();
    } catch (error) {
      note.textContent = t(error.body?.result === "rejected" ? "keyRejected" : "keyShape");
    }
  });
  return el("li", { className: "ai-app" },
    el("div", {}, el("p", { className: "choice-name", textContent: plan.name }),
      el("p", { className: "meta", textContent: t(plan.ready ? "aiSignedIn" : "aiPlanKey") }),
      el("p", { className: "meta", textContent: t(`planTerms_${plan.id}`) === `planTerms_${plan.id}` ? "" : t(`planTerms_${plan.id}`) })),
    plan.ready ? el("div", { className: "ai-body" }, button(t("aiUse"), done, "primary compact")) : form);
}

export async function aiScreen(screen, { back, done }) {
  const title = () => [el("h1", { tabIndex: -1, textContent: t("aiTitle") }), el("p", { className: "lede", textContent: t("aiHint") })];
  screen(...title(), status(t("scanLooking")));
  const [apps, view] = await Promise.all([api("/setup/scan/subscriptions?fresh=1"), api("/connections")]);
  const rows = apps.apps.map((app) => appRow(app, view.subscription.find((s) => s.id === app.id), done));
  rows.push(...view.api.filter((p) => p.plan).map((p) => planRow(p, done)));
  screen(...title(), el("ul", { className: "ai-apps" }, ...rows),
    el("p", { className: "meta", textContent: t("aiListenNote") }),
    el("nav", { className: "step-nav" }, button(t("back"), back)));
}
