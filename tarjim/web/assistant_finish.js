import { api, post } from "./api.js";
import { t } from "./i18n.js";
import { button, el, status, wait } from "./ui.js";

const POLL_MS = 2000;

function toolRow(tool) {
  const state = tool.installed ? "done" : tool.state === "failed" ? "failed" : "busy";
  const label = t(tool.installed ? "toolReady" : tool.state === "failed" ? "toolFailed" : "downloading");
  return el("li", { className: `check ${state}` }, el("span", { className: "check-mark", ariaHidden: "true" }),
    el("span", { className: "check-name", textContent: t(`tool_${tool.id}`) }),
    el("span", { className: "check-value", textContent: `${label} · ${tool.size_gb} GB` }));
}

export async function progressScreen(screen, started, onDone) {
  const ids = Object.keys(started || {});
  if (!ids.length) return onDone();
  const list = el("ul", { className: "checks" });
  const note = status(t("progressHint"));
  screen(el("h1", { tabIndex: -1, textContent: t("progressTitle") }), list, note);
  for (;;) {
    const tools = (await api("/tools").catch(() => [])).filter((tool) => ids.includes(tool.id));
    list.replaceChildren(...tools.map(toolRow));
    if (tools.length && tools.every((tool) => tool.installed)) return onDone();
    const failed = tools.filter((tool) => tool.state === "failed" && !tool.installed);
    if (failed.length && tools.every((tool) => tool.installed || tool.state !== "downloading")) {
      note.textContent = t("progressFailed");
      note.after(button(t("tryAgain"), async () => {
        await Promise.all(failed.map((tool) => post(`/tools/${tool.id}`, {}).catch(() => null)));
        progressScreen(screen, started, onDone);
      }, "primary"));
      return undefined;
    }
    await wait(POLL_MS);
  }
}

export async function readyScreen(screen, finish, extras) {
  const test = status(t("selfTestRunning"));
  const start = el("input", { type: "checkbox", checked: true });
  const done = () => post("/setup", { setup_done: "yes", autostart: start.checked });
  const go = button(t("readyStart"), async () => { await done(); finish(); }, "primary");
  const phone = button(t("phoneReadyButton"), async () => {
    await done();
    location.hash = "#phone";
    location.reload();
  });
  screen(el("h1", { tabIndex: -1, textContent: t("readyTitle") }),
    el("p", { className: "lede", textContent: t("readyHint") }), test,
    el("label", { className: "check-option" }, start, el("span", { textContent: t("autostart") })),
    el("div", { className: "stack ready-phone" }, el("p", { className: "meta", textContent: t("phoneReadyHint") }), phone),
    el("nav", { className: "step-nav" }, button(t("readyExtras"), extras), go));
  const reply = await post("/setup/selftest", { language: document.documentElement.lang }).catch(() => null);
  test.textContent = reply?.ok ? t("selfTestPassed", { text: reply.text }) : t("selfTestFailed");
  test.className = `meta ${reply?.ok ? "ok" : "error"}`;
}
