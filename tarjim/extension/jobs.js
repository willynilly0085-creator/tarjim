import { api, failureText, modeLabel, post, sinceText, stageLabel, stepsFor, t } from "./shared.js";

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

// What a press on a job's button led to, said on that job: the global "tarjim is not running"
// screen is only for when tarjim itself cannot be reached at all.
const PROBLEMS = { offline: "actionOffline", 404: "actionChanged", 409: "actionChanged" };

function say(row, text, kind = "") {
  const note = row.querySelector(".job-note");
  note.textContent = text;
  note.dataset.kind = kind;
  note.hidden = !text;
}

function sayFor(row, text, ms) {
  say(row, text);
  setTimeout(() => { if (row.querySelector(".job-note").textContent === text) say(row, ""); }, ms);
}

// words: { done } said after it worked, { missing } said when the file is gone.
function guarded(row, call, words = {}) {
  return async () => {
    say(row, "");
    try {
      await call();
      if (words.done) sayFor(row, t(words.done), 5000);
    } catch (error) {
      if (error.kind === "token") throw error;  // the pairing screen
      const missing = error.status === 404 && words.missing;
      say(row, t(missing || PROBLEMS[error.kind] || PROBLEMS[error.status] || "actionFailed"), "problem");
    }
  };
}

// Cancel deletes what the job made so far, so it asks first, as tarjim's page does.
function steering(job, act, refresh) {
  const steer = (action) => () => post(`/jobs/${job.id}/${action}`).then(refresh);
  const stop = act(t("cancel"), async () => {
    if (!stop.dataset.sure) return askFirst(stop, ["cancel", "cancelSure", "cancelLabel"]);
    return steer("cancel")();
  });
  named(stop, t("cancelLabel"));
  return [act(t(job.paused ? "resume" : "pause"), steer(job.paused ? "resume" : "pause")), stop];
}

function actionButton(label, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "button-quiet";
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function named(button, label) {
  button.setAttribute("aria-label", label);
  button.title = label;
}

// A press that cannot be undone asks once: [label, question, spoken label] of the button.
function askFirst(button, [label, sure, spoken]) {
  button.dataset.sure = "yes";
  button.textContent = t(sure);
  named(button, t(sure));
  setTimeout(() => {
    delete button.dataset.sure;
    button.textContent = t(label);
    named(button, t(spoken));
  }, 5000);
}

// A finished video is one press from gone from view, so it asks once; its files stay either way.
function removeButton(job, row, refresh) {
  const button = actionButton(t("remove"), guarded(row, async () => {
    if (job.stage === "done" && !button.dataset.sure) return askFirst(button, ["remove", "removeSure", "removeLabel"]);
    await post(`/jobs/${job.id}/remove`);
    rows.delete(job.id);
    document.getElementById("announcer").textContent = t("removed");
    if (document.activeElement === button) document.getElementById("recent-title").focus();
    refresh();
  }));
  button.classList.add("job-remove");
  named(button, t("removeLabel"));
  return button;
}

function actionsFor(job, box, refresh) {
  const ended = job.stage === "failed" || job.stage === "cancelled";
  const wanted = job.stage === "done" ? "done" : ended ? "again" : job.paused ? "paused" : "running";
  if (box.dataset.for === wanted) return;
  box.dataset.for = wanted;
  box.hidden = false;
  const row = box.closest(".job");
  const act = (label, call, words) => actionButton(label, guarded(row, call, words));
  const opened = { done: "opened", missing: "actionMissing" };
  const buttons = wanted === "done"
    ? [act(t(job.mode === "srt" ? "openSrt" : "play"), () => post(`/open/${job.id}`), opened),
       act(t("openFolder"), () => post(`/reveal/${job.id}`), opened)]
    : wanted === "again" ? [act(t("retry"), () => post(`/retry/${job.id}`).then(refresh))]
      : steering(job, act, refresh);
  box.replaceChildren(...buttons, ...(job.finished ? [removeButton(job, row, refresh)] : []));
}

function metaText(job, languages) {
  const language = languages.get(job.target) || job.target;
  const since = job.finished ? "" : ` · ${sinceText(job)}`;
  return `${language} · ${modeLabel(job.mode)}${since}`;
}

function paint(row, job, languages, refresh) {
  if (row.dataset.stage && row.dataset.stage !== job.stage) say(row, "");  // old news for this job
  row.dataset.stage = job.stage;
  row.dataset.paused = String(Boolean(job.paused));
  row.querySelector(".job-title").textContent = job.title;
  row.querySelector(".job-title").title = job.title;
  row.querySelector(".job-stage").textContent = job.paused ? t("stagePaused") : stageLabel(job.stage);
  row.querySelector(".job-meta").textContent = metaText(job, languages);
  const error = row.querySelector(".job-error");
  error.hidden = job.stage !== "failed";
  error.textContent = job.stage === "failed" ? failureText(job) : "";
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
