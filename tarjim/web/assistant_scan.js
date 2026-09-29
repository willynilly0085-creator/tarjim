import { api } from "./api.js";
import { t } from "./i18n.js";
import { button, el } from "./ui.js";

const PARTS = ["device", "tools", "local", "subscriptions", "keys"];
const list = (items) => new Intl.ListFormat(document.documentElement.lang).format(items);

const DESCRIBE = {
  device: (d) => [d.gpu ? t("scanGpu", { name: d.gpu_name, gb: d.vram_gb }) : t("scanNoGpu"),
    t("scanMemory", { memory: d.memory_gb, disk: d.disk_free_gb })],
  tools: (d) => {
    const ready = Object.entries(d.installed).filter(([, yes]) => yes).map(([id]) => t(`tool_${id}`));
    return [ready.length ? t("scanToolsSome", { list: list(ready) }) : t("scanToolsNone")];
  },
  local: (d) => [d.programs.length
    ? list(d.programs.map((p) => t(p.running ? "scanProgramRunning" : "scanProgramStopped", { name: p.name, n: p.models.length })))
    : t("scanLocalNone")],
  subscriptions: (d) => {
    const found = d.apps.filter((a) => a.installed);
    return [found.length
      ? list(found.map((a) => t(a.signed_in ? "scanSignedIn" : "scanSignedOut", { name: a.name })))
      : t("scanSubsNone")];
  },
  keys: (d) => [d.saved.length ? t("scanKeys", { list: d.saved.join("، ") }) : t("scanKeysNone")],
};

function row(part) {
  const value = el("span", { className: "check-value", textContent: t("scanLooking") });
  const item = el("li", { className: "check busy" },
    el("span", { className: "check-mark", ariaHidden: "true" }),
    el("span", { className: "check-name", textContent: t(`scanPart_${part}`) }), value);
  return { item, value };
}

export async function scanScreen(screen) {
  const rows = Object.fromEntries(PARTS.map((part) => [part, row(part)]));
  const done = el("p", { className: "meta", role: "status" });
  screen(el("h1", { tabIndex: -1, textContent: t("scanTitle") }),
    el("p", { className: "lede", textContent: t("scanHint") }),
    el("ul", { className: "checks" }, ...PARTS.map((part) => rows[part].item)), done);
  const found = {};
  await Promise.all(PARTS.map(async (part) => {
    const answer = await api(`/setup/scan/${part}?fresh=1`).catch(() => null);
    found[part] = answer;
    rows[part].item.classList.replace("busy", answer ? "done" : "failed");
    rows[part].value.textContent = answer ? DESCRIBE[part](answer).join(" · ") : t("scanFailed");
  }));
  done.textContent = t("scanDone");
  await new Promise((resolve) => done.after(el("nav", { className: "step-nav" }, button(t("scanSeePlan"), resolve, "primary"))));
  return found;
}
