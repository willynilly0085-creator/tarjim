import { api, post } from "./api.js";
import { t } from "./i18n.js";
import { button, el, status, wait } from "./ui.js";

const POLL_MS = 2000;

// A tool neither installed nor downloading has stopped: it failed, or tarjim restarted and forgot
// the download (its state is back to idle). Either way it waits for "Try again".
const stopped = (tool) => !tool.installed && tool.state !== "downloading";

function toolRow(tool) {
  const state = tool.installed ? "done" : stopped(tool) ? "failed" : "busy";
  const label = t(tool.installed ? "toolReady" : stopped(tool) ? "toolFailed" : "downloading");
  return el("li", { className: `check ${state}` }, el("span", { className: "check-mark", ariaHidden: "true" }),
    el("span", { className: "check-name", textContent: t(`tool_${tool.id}`) }),
    el("span", { className: "check-value", textContent: `${label} · ${tool.size_gb} GB` }));
}

// Why a download stopped, in the downloader's own words: never a failure without its reason.
function reason(tool) {
  return el("p", { className: "job-error", dir: "auto", textContent: `${t(`tool_${tool.id}`)}: ${tool.detail}` });
}

// Every tool watched here started from the plan, its license accepted there, so "Try again"
// starts it the same way.
function offerRetry(note, halted, again) {
  note.textContent = t(halted.some((tool) => tool.state === "failed") ? "progressFailed" : "progressStopped");
  note.className = "meta";
  note.after(...halted.filter((tool) => tool.detail).map(reason), button(t("tryAgain"), async () => {
    await Promise.all(halted.map((tool) => post(`/tools/${tool.id}`, { accept_license: true }).catch(() => null)));
    again();
  }, "primary"));
}

// One look at the downloads: the watched tools once none is still downloading, else null. While
// tarjim cannot be reached the note says so instead of a progress that is not happening.
async function look(ids, list, note) {
  const all = await api("/tools").catch(() => null);
  note.textContent = t(all ? "progressHint" : "sendOffline");
  note.className = all ? "meta" : "meta error";
  const tools = (all || []).filter((tool) => ids.includes(tool.id));
  if (all) list.replaceChildren(...tools.map(toolRow));
  return tools.length && tools.every((tool) => tool.installed || stopped(tool)) ? tools : null;
}

const watched = (started) => Object.entries(started || {})
  .filter(([, result]) => result === "started" || result === "busy").map(([id]) => id);

export async function progressScreen(screen, started, onDone) {
  const ids = watched(started);  // a tool refused at the start (license, manual) never downloads
  if (!ids.length) return onDone();
  const list = el("ul", { className: "checks" });
  const note = status(t("progressHint"));
  screen(el("h1", { tabIndex: -1, textContent: t("progressTitle") }), list, note);
  for (;;) {
    const settled = await look(ids, list, note);
    if (settled?.every((tool) => tool.installed)) return onDone();
    if (settled) return offerRetry(note, settled.filter(stopped), () => progressScreen(screen, started, onDone));
    await wait(POLL_MS);
  }
}

export async function readyScreen(screen, finish, extras) {
  const test = status(t("selfTestRunning"));
  const start = el("input", { type: "checkbox", checked: true });
  const fresh = el("input", { type: "checkbox", checked: true });
  const done = () => post("/setup", { setup_done: "yes", autostart: start.checked, auto_update: fresh.checked });
  const go = button(t("readyStart"), async () => { await done(); finish(); }, "primary");
  const phone = button(t("phoneReadyButton"), async () => {
    await done();
    location.hash = "#phone";
    location.reload();
  });
  screen(el("h1", { tabIndex: -1, textContent: t("readyTitle") }),
    el("p", { className: "lede", textContent: t("readyHint") }), test,
    el("label", { className: "check-option" }, start, el("span", { textContent: t("autostart") })),
    el("label", { className: "check-option" }, fresh, el("span", { textContent: t("autoUpdate") })),
    el("div", { className: "stack ready-phone" }, el("p", { className: "meta", textContent: t("phoneReadyHint") }), phone),
    el("nav", { className: "step-nav" }, button(t("readyExtras"), extras), go));
  const reply = await post("/setup/selftest", { language: document.documentElement.lang }).catch(() => null);
  test.textContent = reply?.ok ? t("selfTestPassed", { text: reply.text }) : t("selfTestFailed");
  test.className = `meta ${reply?.ok ? "ok" : "error"}`;
}
