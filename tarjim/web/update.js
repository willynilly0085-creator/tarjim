import { $, api, post } from "./api.js";
import { t } from "./i18n.js";
import { button, el, wait } from "./ui.js";

const BACK_TRIES = 240;

async function waitForNewEngine(before) {
  for (let i = 0; i < BACK_TRIES; i += 1) {
    await wait(3000);
    const now = await api("/update").catch(() => null);
    if (now && now.current !== before) return location.reload();
    if (now?.failed) return false;
  }
  return false;
}

async function apply(state, box) {
  box.replaceChildren(el("span", { textContent: t("updating") }));
  const reply = await post("/update/apply", {}).catch((error) => error.body || {});
  if (reply.error === "busy") return box.replaceChildren(el("span", { textContent: t("updateBusy") }));
  if (!reply.started || (await waitForNewEngine(state.current)) === false) {
    box.replaceChildren(el("span", { textContent: t("updateFailed") }));
  }
}

export async function showUpdate() {
  const state = await api("/update").catch(() => null);
  const box = $("update-banner");
  box.hidden = !state?.available;
  if (box.hidden) return;
  const words = el("span", { textContent: t("updateAvailable", { version: state.latest }) });
  box.replaceChildren(words, state.can_install ? button(t("updateNow"), () => apply(state, box), "primary small")
    : el("span", { className: "meta", textContent: t("updateManual") }));
}

const REACH = { model: "knownIssueModel", unused: "knownIssueUnused" };

// Each library once, then one line per reason with the advisory ids under it.
function issueGroups(issues) {
  const libraries = new Map();
  for (const issue of issues) {
    const library = `${issue.package} ${issue.installed}`;
    const reasons = libraries.get(library) || new Map();
    reasons.set(issue.reach, [...(reasons.get(issue.reach) || []), issue.id]);
    libraries.set(library, reasons);
  }
  return libraries;
}

const reasonLine = ([reach, ids]) => el("p", { className: "known-issues-reason" },
  el("span", { textContent: t(REACH[reach] || "knownIssueOther") }),
  el("span", { className: "meta known-issues-ids", dir: "ltr" },
    ids.flatMap((id, at) => [at ? ", " : "", el("span", { className: "known-issues-id", textContent: id })])));

// Published vulnerabilities that still apply to the versions installed here (tarjim/known_issues.json).
function showKnownIssues(state) {
  const issues = state.known_issues || [];
  $("known-issues").hidden = issues.length === 0;
  $("known-issues-more").href = state.known_issues_details || "";
  $("known-issues-list").replaceChildren(...[...issueGroups(issues)].map(([library, reasons]) => el("li", {},
    el("span", { className: "known-issues-library", dir: "ltr", textContent: library }),
    ...[...reasons].map(reasonLine))));
}

export function fillUpdateChoice(setup) {
  $("auto-update").checked = setup.auto_update !== false;
  $("auto-update").onchange = () => post("/setup", { auto_update: $("auto-update").checked });
  api("/update").then((state) => {
    $("version-line").textContent = t("versionLine", { version: state.current });
    showKnownIssues(state);
  }).catch(() => {});
}
