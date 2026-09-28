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
  const gpu = s.gpu ? `${s.gpu.name} (${s.gpu.memory_gb} GB)${s.gpu.usable ? "" : ` · ${t("gpuUnused")}`}` : t("gpuNone");
  $("facts").replaceChildren(...fact(t("gpu"), gpu, s.gpu && !s.gpu.usable), ...fact(t("memory"), `${s.memory_gb} GB`),
    ...fact(t("disk"), `${s.disk_free_gb} GB`),
    ...fact(t("ffmpegRow"), t(s.ffmpeg ? "present" : "ffmpegLater"), !s.ffmpeg));
  const local = s.local_ready ? "localCapable" : s.gpu && !s.gpu.usable ? "localAfterFix" : "localNot";
  $("device-advice").textContent = `${t("recommendCloud")} ${t(local)}`;
  $("gpu-fix").hidden = !(s.gpu && s.gpu.fix);
  $("gpu-fix-command").textContent = s.gpu?.fix || "";
}

function consentBox(tool, button) {
  const box = Object.assign(document.createElement("input"), { type: "checkbox" });
  const label = Object.assign(document.createElement("label"), { className: "consent" });
  label.append(box, document.createTextNode(` ${t("consentCheck", { name: tool.license })}`));
  button.disabled = true;
  box.addEventListener("change", () => { button.disabled = !box.checked; });
  return label;
}

function toolAction(tool, refresh) {
  if (tool.installed) return Object.assign(document.createElement("span"), { className: "ready", textContent: t("installed") });
  if (tool.state === "downloading") return Object.assign(document.createElement("span"), { className: "meta", textContent: t("downloading") });
  const button = Object.assign(document.createElement("button"), {
    type: "button", className: tool.required ? "primary small" : "button-quiet",
    textContent: t(tool.state === "failed" ? "retry" : "download"),
  });
  button.addEventListener("click", () => post(`/tools/${tool.id}`, { accept_license: tool.consent }).finally(refresh));
  if (!tool.consent) return button;
  const wrap = Object.assign(document.createElement("div"), { className: "stack" });
  wrap.append(consentBox(tool, button), button);
  return wrap;
}

function licenseLine(tool) {
  const link = Object.assign(document.createElement("a"), { className: "text-link", href: tool.license_url,
    target: "_blank", rel: "noopener noreferrer", textContent: tool.license });
  const note = tool.commercial ? "" : ` · ${t("nonCommercial")}`;
  const line = Object.assign(document.createElement("p"), { className: "meta tool-license" });
  line.append(`${t("licenseLabel")}: `, link, note);
  return line;
}

export async function renderTools(state, refresh = () => renderTools(state)) {
  state.tools = await api("/tools");
  $("tool-list").replaceChildren(...state.tools.map((tool) => {
    const row = $("tool-row").content.firstElementChild.cloneNode(true);
    row.querySelector(".tool-name").textContent = `${t(`tool_${tool.id}`)} · ${t(tool.required ? "required" : "optional")}`;
    row.querySelector(".tool-hint").textContent = tool.state === "failed" ? t("failed") : t(`tool_${tool.id}_hint`);
    row.querySelector(".tool-hint").after(licenseLine(tool));
    row.querySelector(".tool-size").textContent = t("sizeGb", { n: tool.size_gb });
    row.querySelector(".tool-action").replaceChildren(toolAction(tool, refresh));
    return row;
  }));
  return state.tools.some((tool) => tool.state === "downloading");
}
