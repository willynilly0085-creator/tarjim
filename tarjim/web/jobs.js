import { $, api, post } from "./api.js";
import { t } from "./i18n.js";

const STAGES = ["downloading", "hearing", "translating", "writing", "burning", "dubbing"];
const ERRORS = ["quota", "key", "download", "tools", "dub"];
const rows = new Map();
const seen = new Map();

function steps(job) {
  const wanted = { downloading: job.link, burning: job.mode !== "srt", dubbing: job.mode.startsWith("dub") };
  return STAGES.filter((stage) => wanted[stage] ?? true);
}

function track(job, list) {
  const all = steps(job);
  const current = job.stage === "done" ? all.length : all.indexOf(job.stage);
  list.replaceChildren(...all.map((_, i) => Object.assign(document.createElement("li"), {
    className: i < current ? "past" : i === current && job.stage !== "queued" ? "now" : "",
  })));
}

function button(label, action) {
  const el = Object.assign(document.createElement("button"), { type: "button", className: "button-quiet", textContent: label });
  el.addEventListener("click", action);
  return el;
}

function actions(job, box, refresh) {
  const kind = job.stage === "done" ? "done" : job.stage === "failed" ? "failed" : "";
  if (box.dataset.kind === kind) return;
  box.dataset.kind = kind;
  box.hidden = !kind;
  box.replaceChildren(...(kind === "done"
    ? [button(t("play"), () => post(`/open/${job.id}`)), button(t("openFolder"), () => post(`/reveal/${job.id}`))]
    : kind === "failed" ? [button(t("retry"), () => post(`/retry/${job.id}`).then(refresh))] : []));
}

function modeText(mode) {
  return t(mode.startsWith("dub") ? "outputDub" : mode === "srt" ? "outputSrt" : "outputBurn");
}

function paint(row, job, languages, refresh) {
  row.dataset.stage = job.stage;
  row.querySelector(".job-title").textContent = job.title;
  row.querySelector(".job-stage").textContent = t(`stage_${job.stage}`);
  row.querySelector(".job-meta").textContent = `${languages.get(job.target) || job.target} · ${modeText(job.mode)}`;
  const error = row.querySelector(".job-error");
  error.hidden = job.stage !== "failed";
  error.textContent = job.stage === "failed" ? t(`err_${ERRORS.includes(job.error_code) ? job.error_code : "unknown"}`) : "";
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
