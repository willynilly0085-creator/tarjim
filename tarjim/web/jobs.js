import { $, api, post } from "./api.js";
import { t } from "./i18n.js";
import { problem } from "./problems.js";

const STAGES = ["downloading", "hearing", "timing", "translating", "writing", "burning", "dubbing"];
const ACTION = { gone: "actionGone", job: "actionStale", open: "actionOpen" };
const ERRORS = ["updated", "media", "long", "list", "account", "quota", "signin", "key", "download", "tools", "dub"];
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

// A button whose request fails says why under its job, instead of doing nothing.
function guarded(job, work) {
  return async () => {
    const box = rows.get(job.id)?.querySelector(".job-problem");
    if (box) box.hidden = true;
    try {
      await work();
    } catch (error) {
      if (!box) return;
      box.textContent = problem(error, ACTION);
      box.hidden = false;
    }
  };
}

function named(el, label) {
  el.setAttribute("aria-label", label);
  el.title = label;
}

// A press that cannot be undone asks once: [label, question, spoken label] of the button.
function askFirst(el, [label, sure, spoken]) {
  el.dataset.sure = "yes";
  el.textContent = t(sure);
  named(el, t(sure));
  setTimeout(() => {
    delete el.dataset.sure;
    el.textContent = t(label);
    named(el, t(spoken));
  }, 5000);
}

// Cancel deletes what the job made so far, so it asks first.
function steering(job, refresh) {
  const steer = (action) => guarded(job, () => post(`/jobs/${job.id}/${action}`).then(refresh));
  const words = ["cancel", "cancelSure", "cancelLabel"];
  const stop = button(t("cancel"), () => (stop.dataset.sure ? steer("cancel")() : askFirst(stop, words)));
  named(stop, t("cancelLabel"));
  return [button(t(job.paused ? "resume" : "pause"), steer(job.paused ? "resume" : "pause")), stop];
}

// A finished video is one press from gone from view, so it asks once; its files stay either way.
function removeButton(job, refresh) {
  const el = button(t("remove"), guarded(job, async () => {
    if (job.stage === "done" && !el.dataset.sure) return askFirst(el, ["remove", "removeSure", "removeLabel"]);
    await post(`/jobs/${job.id}/remove`);
    rows.delete(job.id);
    $("announcer").textContent = t("removed");
    if (document.activeElement === el) $("recent-title").focus();
    refresh();
  }));
  el.classList.add("job-remove");
  named(el, t("removeLabel"));
  return el;
}

function actions(job, box, refresh) {
  const ended = job.stage === "failed" || job.stage === "cancelled";
  const kind = job.stage === "done" ? "done" : ended ? "again" : job.paused ? "paused" : "running";
  if (box.dataset.kind === kind) return;
  box.dataset.kind = kind;
  box.hidden = false;
  box.closest(".job").querySelector(".job-problem").hidden = true;  // a new state, a fresh start
  box.replaceChildren(...(kind === "done" ? opening(job)
    : kind === "again" ? [button(t("retry"), guarded(job, () => post(`/retry/${job.id}`).then(refresh)))]
      : steering(job, refresh)),
  ...(job.finished ? [removeButton(job, refresh)] : []));
}

// A subtitle file alone opens as text, so its button says so rather than "Play".
function opening(job) {
  const play = job.mode === "srt" ? "openSrt" : "play";
  return [button(t(play), guarded(job, () => post(`/open/${job.id}`))),
    button(t("openFolder"), guarded(job, () => post(`/reveal/${job.id}`)))];
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

// After a few polls in a row that cannot reach tarjim the page says so, and the jobs dim, since
// their state is the last one known and not what happens now.
const MISSES = 3;
let misses = 0;

// failed: the error of this poll, or null when it worked.
function reachable(failed) {
  misses = failed ? misses + 1 : 0;
  const down = misses >= MISSES;
  let banner = $("jobs-offline");
  if (!banner && down) {
    banner = Object.assign(document.createElement("p"), { id: "jobs-offline", className: "error", role: "alert" });
    $("jobs").before(banner);
  }
  if (banner) {
    banner.textContent = down ? problem(failed) : "";
    banner.hidden = !down;
  }
  $("jobs").classList.toggle("stale", down);
}

export function watchJobs(languages) {
  const refresh = async () => {
    let failed = null;
    const jobs = await api("/jobs").catch((error) => { failed = error; return null; });
    reachable(failed);
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
