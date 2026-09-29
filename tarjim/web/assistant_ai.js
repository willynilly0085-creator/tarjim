import { api, post } from "./api.js";
import { t } from "./i18n.js";
import { signInPanel } from "./signin.js";
import { button, el, status, wait } from "./ui.js";

const INSTALL_POLL_MS = 4000;
const INSTALL_ROUNDS = 150;

async function install(sub, body, done) {
  body.replaceChildren(status(t("aiInstalling")));
  const reply = await post("/connections/install-app", { provider: sub.id }).catch(() => null);
  if (!reply) return body.replaceChildren(status(t("aiInstallFailed"), "error"));
  for (let round = 0; round < INSTALL_ROUNDS; round += 1) {
    await wait(INSTALL_POLL_MS);
    const now = (await api("/connections").catch(() => null))?.subscription.find((s) => s.id === sub.id);
    if (now?.install_failed) return body.replaceChildren(status(t("aiInstallFailed"), "error"));
    if (now?.ready) return body.replaceChildren(signInPanel(now, done));
  }
  return body.replaceChildren(status(t("aiInstallFailed"), "error"));
}

function action(app, sub, body, done) {
  if (app.signed_in) return [button(t("aiUse"), done, "primary compact")];
  if (app.installed) return [signInPanel(sub, done)];
  if (sub.can_install) return [button(t("aiInstall"), () => install(sub, body, done))];
  const site = sub.install.startsWith("http");
  return [status(t(site ? "aiFromSite" : "aiNeedsNode")), el("a", { className: "text-link", href: site ? sub.install : "https://nodejs.org/",
    target: "_blank", rel: "noopener noreferrer", textContent: t(site ? "aiOpenSite" : "aiGetNode") })];
}

function appRow(app, sub, done) {
  const state = app.signed_in ? "aiSignedIn" : app.installed ? "aiInstalled" : "aiMissing";
  const body = el("div", { className: "ai-body" });
  body.append(...action(app, sub, body, done));
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
