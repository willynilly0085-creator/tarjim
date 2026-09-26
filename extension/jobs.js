import { api, errorLabel, modeLabel, post, stageLabel, stepsFor, t } from "./shared.js";

const rows = new Map();
const spoken = new Map();

function trackFor(job, list) {
  const steps = stepsFor(job);
  const at = steps.indexOf(job.stage);
  const current = job.stage === "done" ? steps.length : at;
  list.replaceChildren(...steps.map((_, index) => {
    const item = document.createElement("li");
    if (index < current) item.className = "past";
    if (index === current && job.stage !== "queued") item.className = "now";
    return item;
  }));
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
  const wanted = job.stage === "done" ? "done" : job.stage === "failed" ? "failed" : "";
  if (box.dataset.for === wanted) return;
  box.dataset.for = wanted;
  box.hidden = !wanted;
  const buttons = wanted === "done"
    ? [actionButton(t("play"), () => post(`/open/${job.id}`)),
       actionButton(t("openFolder"), () => post(`/reveal/${job.id}`))]
    : wanted === "failed" ? [actionButton(t("retry"), () => post(`/retry/${job.id}`).then(refresh))] : [];
  box.replaceChildren(...buttons);
}

function metaText(job, languages) {
  const language = languages.get(job.target) || job.target;
  return `${language} · ${modeLabel(job.mode)}`;
}

function paint(row, job, languages, refresh) {
  row.dataset.stage = job.stage;
  row.querySelector(".job-title").textContent = job.title;
  row.querySelector(".job-title").title = job.title;
  row.querySelector(".job-stage").textContent = stageLabel(job.stage);
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
