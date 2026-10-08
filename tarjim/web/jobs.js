import { $, api, post } from "./api.js";
import { t } from "./i18n.js";

const STAGES = ["downloading", "hearing", "timing", "translating", "writing", "burning", "dubbing"];
const ERRORS = ["quota", "signin", "key", "download", "tools", "dub"];
const rows = new Map();
const seen = new Map();

function steps(job) {
  const wanted = { downloading: job.link, burning: job.mode !== "srt", dubbing: job.mode.startsWith("dub") };
  return STAGES.filter((stage) => wanted[stage] ?? true);
}

function stepItem(stage, index, current, labelled) {
  const item = document.createElement("li");
  item.className = index < current ? "past" : index === current ? "now" : "";
  item.append(Object.assign(document.createElement("i"), { className: "dash" }));
  if (labelled) item.append(Object.assign(document.createElement("span"), { className: "dash-label", textContent: t(`step_${stage}`) }));
  return item;
}

function track(job, list) {
  const all = steps(job);
  const current = job.stage === "done" ? all.length : all.indexOf(job.stage);
  const key = `${job.stage}|${job.paused}|${job.finished}`;
  if (list.dataset.key === key) return;
  list.dataset.key = key;
  list.replaceChildren(...all.map((stage, i) => stepItem(stage, i, current, !job.finished)));
}

function button(label, action) {
  const el = Object.assign(document.createElement("button"), { type: "button", className: "button-quiet", textContent: label });
  el.addEventListener("click", action);
  return el;
}

function steering(job, refresh) {
  const steer = (action) => () => post(`/jobs/${job.id}/${action}`).then(refresh);
  return [button(t(job.paused ? "resume" : "pause"), steer(job.paused ? "resume" : "pause")),
    button(t("cancel"), steer("cancel"))];
}

function actions(job, box, refresh) {
  const ended = job.stage === "failed" || job.stage === "cancelled";
  const kind = job.stage === "done" ? "done" : ended ? "again" : job.paused ? "paused" : "running";
  if (box.dataset.kind === kind) return;
  box.dataset.kind = kind;
  box.hidden = false;
  box.replaceChildren(...(kind === "done"
    ? [button(t("play"), () => post(`/open/${job.id}`)), button(t("openFolder"), () => post(`/reveal/${job.id}`))]
    : kind === "again" ? [button(t("retry"), () => post(`/retry/${job.id}`).then(refresh))] : steering(job, refresh)));
}
function modeText(mode) {
  return t(mode.startsWith("dub") ? "outputDub" : mode === "srt" ? "outputSrt" : "outputBurn");
}

// Every failure says where it stopped, what it means and the real reason.
function failure(job) {
  const where = job.failed_at ? `${t("failedAt", { stage: t(`stage_${job.failed_at}`) })} ` : "";
  const meaning = t(`err_${ERRORS.includes(job.error_code) ? job.error_code : "unknown"}`);
  return `${where}${meaning}${job.detail ? `\n${t("errorDetail", { detail: job.detail })}` : ""}`;
}

function paint(row, job, languages, refresh) {
  row.dataset.stage = job.stage;
  row.dataset.paused = String(Boolean(job.paused));
  row.querySelector(".job-title").textContent = job.title;
  row.querySelector(".job-stage").textContent = t(job.paused ? "stage_paused" : `stage_${job.stage}`);
  const minutes = Math.floor((Date.now() / 1000 - job.created) / 60);
  const since = job.finished ? "" : ` · ${minutes < 1 ? t("agoNow") : t("agoMinutes", { n: minutes })}`;
  row.querySelector(".job-meta").textContent = `${languages.get(job.target) || job.target} · ${modeText(job.mode)}${since}`;
  const error = row.querySelector(".job-error");
  error.hidden = job.stage !== "failed";
  error.textContent = job.stage === "failed" ? failure(job) : "";
  track(job, row.querySelector(".track"));
  actions(job, row.querySelector(".job-actions"), refresh);
  const before = seen.get(job.id);
  seen.set(job.id, job.stage);
  if (before && before !== job.stage && job.finished) $("announcer").textContent = `${job.title}: ${t(`stage_${job.stage}`)}`;
}

export function watchJobs(languages) {
  const refresh = async () => {
    const jobs = await api("/jobs").catch(() => null);
    if (!jobs) return;
    $("empty").hidden = jobs.length > 0;
    const list = $("jobs");
    const ordered = jobs.map((job) => {
      const row = rows.get(job.id) || $("job-row").content.firstElementChild.cloneNode(true);
      rows.set(job.id, row);
      paint(row, job, languages, refresh);
      return row;
    });
    if (ordered.some((row, i) => list.children[i] !== row) || ordered.length !== list.children.length) {
      list.replaceChildren(...ordered);
    }
  };
  refresh();
  return setInterval(refresh, 2000);
}
