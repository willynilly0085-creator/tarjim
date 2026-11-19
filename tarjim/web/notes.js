import { t } from "./i18n.js";

// A finished job that knows something is not right says so, with each thing and where it is
// (2026-11-08): speech left without words or lines no engine translated used to look like plain
// success. A readability warning alone is listed, quietly, but the job stays plain done.

const isolate = (text) => `⁦${text}⁩`;

function clock(seconds) {
  const whole = Math.max(0, Math.round(seconds));
  return isolate(`${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`);
}

function times(at) {
  return new Intl.ListFormat(document.documentElement.lang || "en", { type: "unit" }).format(at.map(clock));
}

// Models are named left to right inside any language, so "Gemini 3.8 Flash" keeps its order in
// Arabic (2026-11-19: a model other than the one picked translated, and only the log said so).
function models(names) {
  return new Intl.ListFormat(document.documentElement.lang || "en", { type: "conjunction" }).format(names.map(isolate));
}

export function troubled(job) {
  return job.stage === "done" && (job.notes || []).some((note) => note.problem);
}

export function stageLabel(job) {
  if (job.paused) return t("stage_paused");
  return t(troubled(job) ? "stage_doneNotes" : `stage_${job.stage}`);
}

// An engine that stopped partway says why in the words a failed job uses (err_*), and what it
// said, so a used-up quota reads as "come back tomorrow", not as a finished job.
function words(note) {
  const reason = note.reason ? t(`err_${note.reason}`) : "";
  const named = { picked: isolate(note.picked || ""), used: models(note.used || []) };
  const text = t(`note_${note.kind}`, { n: note.count, at: times(note.at || []), share: note.share, reason, ...named });
  return note.detail ? `${text}
${t("errorDetail", { detail: note.detail })}` : text;
}

function item(note) {
  return Object.assign(document.createElement("li"), { className: note.problem ? "" : "note-quiet", textContent: words(note) });
}

export function showNotes(row, job) {
  const notes = job.stage === "done" ? job.notes || [] : [];
  row.dataset.notes = String(troubled(job));
  const list = row.querySelector(".job-notes");
  const key = `${document.documentElement.lang}|${JSON.stringify(notes)}`;
  if (list.dataset.key === key) return;
  list.dataset.key = key;
  list.replaceChildren(...notes.map(item));
  list.hidden = notes.length === 0;
}
