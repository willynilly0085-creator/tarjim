// The quiet request for a star on GitHub (tarjim/star.py). The engine says when it is due (after
// enough finished translations) and keeps the answer; the card is asked for only while no job
// runs, and a star is given only on the person's own press: by their gh when it is signed in,
// otherwise on the GitHub page this opens. The same card as the page's (tarjim/web/star.js).
import { $ } from "./dom.js";
import { api, post, t } from "./shared.js";

const state = { seen: -1, page: "", wired: false };
const SAID_FOR = 6000;

function leave() {
  const card = $("star");
  if (card.contains(document.activeElement)) $("recent-title").focus();  // focus is not lost
  card.classList.add("leaving");
  setTimeout(() => { card.hidden = true; card.classList.remove("leaving"); }, 220);
}

function say(answer) {
  const card = $("star");
  card.dataset.said = answer;
  $("star-said").textContent = t(answer === "starred" ? "starThanks" : "starOpened");
  $("star-said").focus();
  setTimeout(leave, SAID_FOR);
}

async function star() {
  $("star").querySelectorAll("button").forEach((button) => { button.disabled = true; });
  $("star-yes").textContent = t("starWorking");
  const answer = (await post("/star", { choice: "star" }).catch(() => ({}))).answer || "opened";
  say(answer);
  if (answer !== "starred") chrome.tabs.create({ url: state.page });
}

async function skip(choice) {
  leave();
  await post("/star", { choice }).catch(() => {});
}

function wire() {
  $("star-yes").addEventListener("click", star);
  $("star-later").addEventListener("click", () => skip("later"));
  $("star-no").addEventListener("click", () => skip("never"));
  state.wired = true;
}

function show(view) {
  state.page = view.page;
  if (!view.ask || !$("star").hidden) return;
  if (!state.wired) wire();
  $("star").hidden = false;
}

// Called with each fresh list of jobs: asks again only when nothing runs and the count changed.
export function noticeJobs(jobs) {
  if (jobs.some((job) => !job.finished)) return;
  const done = jobs.filter((job) => job.stage === "done").length;
  if (done === state.seen) return;
  state.seen = done;
  api("/star").then(show, () => {});
}
