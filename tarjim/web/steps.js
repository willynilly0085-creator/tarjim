import { $, api, post } from "./api.js";
import { t } from "./i18n.js";

function fact(term, value, bad = false) {
  const dt = document.createElement("dt");
  const dd = document.createElement("dd");
  dt.textContent = term;
  dd.append(Object.assign(document.createElement("bdi"), { textContent: value }));
  dd.classList.toggle("bad", bad);
  return [dt, dd];
}

export async function renderDevice(state) {
  state.system ??= await api("/system");
  const s = state.system;
  const gpu = s.gpu ? `${s.gpu.name} (${s.gpu.memory_gb} GB)` : t("gpuNone");
  $("facts").replaceChildren(...fact(t("gpu"), gpu), ...fact(t("memory"), `${s.memory_gb} GB`),
    ...fact(t("disk"), `${s.disk_free_gb} GB`),
    ...fact(t("ffmpegRow"), t(s.ffmpeg ? "present" : "missing"), !s.ffmpeg));
  $("device-advice").textContent = `${t("recommendCloud")} ${t(s.local_ready ? "localCapable" : "localNot")}`;
}

function toolAction(tool, refresh) {
  if (tool.installed) return Object.assign(document.createElement("span"), { className: "ready", textContent: t("installed") });
  if (tool.state === "downloading") return Object.assign(document.createElement("span"), { className: "meta", textContent: t("downloading") });
  const button = Object.assign(document.createElement("button"), {
    type: "button", className: tool.required ? "primary small" : "button-quiet",
    textContent: t(tool.state === "failed" ? "retry" : "download"),
  });
  button.addEventListener("click", () => post(`/tools/${tool.id}`).finally(refresh));
  return button;
}

export async function renderTools(state) {
  state.tools = await api("/tools");
  const refresh = () => renderTools(state);
  $("tool-list").replaceChildren(...state.tools.map((tool) => {
    const row = $("tool-row").content.firstElementChild.cloneNode(true);
    row.querySelector(".tool-name").textContent = `${t(`tool_${tool.id}`)} · ${t(tool.required ? "required" : "optional")}`;
    row.querySelector(".tool-hint").textContent = tool.state === "failed" ? t("failed") : t(`tool_${tool.id}_hint`);
    row.querySelector(".tool-size").textContent = t("sizeGb", { n: tool.size_gb });
    row.querySelector(".tool-action").replaceChildren(toolAction(tool, refresh));
    return row;
  }));
  return state.tools.some((tool) => tool.state === "downloading");
}
