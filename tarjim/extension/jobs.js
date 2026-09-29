import { api, errorLabel, modeLabel, post, sinceText, stageLabel, stepsFor, t } from "./shared.js";

const rows = new Map();
const spoken = new Map();

function stepItem(stage, index, current, labelled) {
  const item = document.createElement("li");
  item.className = index < current ? "past" : index === current ? "now" : "";
  item.append(Object.assign(document.createElement("i"), { className: "bar" }));
  if (labelled) item.append(Object.assign(document.createElement("span"), { className: "step", textContent: t(`step_${stage}`) }));
  return item;
}

function trackFor(job, list) {
  const steps = stepsFor(job);
  const current = job.stage === "done" ? steps.length : steps.indexOf(job.stage);
  const key = `${job.stage}|${job.paused}|${job.finished}`;
  if (list.dataset.key === key) return;
  list.dataset.key = key;
  list.replaceChildren(...steps.map((stage, index) => stepItem(stage, index, current, !job.finished)));
}

function steering(job, refresh) {
  const steer = (action) => () => post(`/jobs/${job.id}/${action}`).then(refresh);
  return [actionButton(t(job.paused ? "resume" : "pause"), steer(job.paused ? "resume" : "pause")),
    actionButton(t("cancel"), steer("cancel"))];
}

function actionButton(label, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "button-quiet";
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function actionsFor(job, box, refresh) {
  const ended = job.stage === "failed" || job.stage === "cancelled";
  const wanted = job.stage === "done" ? "done" : ended ? "again" : job.paused ? "paused" : "running";
  if (box.dataset.for === wanted) return;
  box.dataset.for = wanted;
  box.hidden = false;
  const buttons = wanted === "done"
    ? [actionButton(t("play"), () => post(`/open/${job.id}`)),
       actionButton(t("openFolder"), () => post(`/reveal/${job.id}`))]
    : wanted === "again" ? [actionButton(t("retry"), () => post(`/retry/${job.id}`).then(refresh))]
      : steering(job, refresh);
  box.replaceChildren(...buttons);
}

function metaText(job, languages) {
  const language = languages.get(job.target) || job.target;
  const since = job.finished ? "" : ` · ${sinceText(job)}`;
  return `${language} · ${modeLabel(job.mode)}${since}`;
}

function paint(row, job, languages, refresh) {
  row.dataset.stage = job.stage;
  row.dataset.paused = String(Boolean(job.paused));
  row.querySelector(".job-title").textContent = job.title;
  row.querySelector(".job-title").title = job.title;
  row.querySelector(".job-stage").textContent = job.paused ? t("stagePaused") : stageLabel(job.stage);
  row.querySelector(".job-meta").textContent = metaText(job, languages);
  const error = row.querySelector(".job-error");
  error.hidden = job.stage !== "failed";
  error.textContent = job.stage === "failed" ? errorLabel(job) : "";
  trackFor(job, row.querySelector(".track"));
  actionsFor(job, row.querySelector(".job-actions"), refresh);
}

function announce(job) {
  const before = spoken.get(job.id);
  spoken.set(job.id, job.stage);
  if (before && before !== job.stage && job.finished) {
    document.getElementById("announcer").textContent = `${job.title}: ${stageLabel(job.stage)}`;
  }
}

export function renderJobs(jobs, languages, refresh) {
  const list = document.getElementById("jobs");
  const template = document.getElementById("job-template");
  document.getElementById("empty").hidden = jobs.length > 0;
  const ordered = jobs.map((job) => {
    let row = rows.get(job.id);
    if (!row) {
      row = template.content.firstElementChild.cloneNode(true);
      rows.set(job.id, row);
    }
    paint(row, job, languages, refresh);
    announce(job);
    return row;
  });
  const same = ordered.length === list.children.length && ordered.every((row, i) => list.children[i] === row);
  if (!same) list.replaceChildren(...ordered);
}

export function watchJobs(languages) {
  const refresh = async () => {
    try {
      renderJobs(await api("/jobs"), languages, refresh);
    } catch {
      /* the connection state is shown by the header */
    }
  };
  refresh();
  return setInterval(refresh, 2000);
}
