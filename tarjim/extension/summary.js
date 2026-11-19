import { t, uiLanguage } from "./shared.js";

// What a finished job carries besides its files, as tarjim's page shows it: a summary ready to
// post (a short text that fits a tweet, and a longer one kept folded), and a line saying how many
// things tarjim found to check in its own work. Each text has its own Copy, so what is pasted is
// exactly what is shown (2026-11-12: the page had both and this panel showed neither).

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

function part(text, name) {
  const words = Object.assign(document.createElement("p"), { className: "job-post-text", textContent: text, dir: "auto" });
  const copy = Object.assign(document.createElement("button"), { type: "button", className: "button-quiet", textContent: t("copy") });
  copy.setAttribute("aria-label", `${t("copy")}: ${name}`);
  copy.addEventListener("click", async () => {
    if (!(await copyText(text))) return;
    copy.textContent = t("copied");
    setTimeout(() => { copy.textContent = t("copy"); }, 2500);
  });
  const box = Object.assign(document.createElement("div"), { className: "job-post-part" });
  box.append(words, copy);
  return box;
}

function longer(text) {
  const fold = document.createElement("details");
  fold.append(Object.assign(document.createElement("summary"), { textContent: t("postLonger") }), part(text, t("postLonger")));
  return fold;
}

// Painted once per text: the jobs are asked for every two seconds, and a repaint would close the
// longer post under the reader and reset a "Copied".
export function showPost(row, job) {
  const box = row.querySelector(".job-post");
  const post = job.stage === "done" ? job.post : null;
  const key = post ? `${post.short}\n${post.long}` : "";
  if (box.dataset.key === key) return;
  box.dataset.key = key;
  box.hidden = !post;
  if (!post) return box.replaceChildren();
  const title = Object.assign(document.createElement("p"), { className: "meta", textContent: t("postTitle") });
  box.replaceChildren(title, part(post.short, t("postTitle")), ...(post.long ? [longer(post.long)] : []));
}

// A model other than the one picked is named here too, not only counted: a person believed the
// picked model had translated their video (2026-11-19). Names stay left to right inside Arabic.
const isolate = (text) => `⁦${text}⁩`;

function otherModel(note) {
  const used = new Intl.ListFormat(uiLanguage(), { type: "conjunction" }).format((note.used || []).map(isolate));
  return t("jobOtherModel", isolate(note.picked || ""), used);
}

export function showNotes(row, job) {
  const notes = job.stage === "done" ? job.notes || [] : [];
  const found = notes.filter((note) => note.problem).length;
  const swapped = notes.find((note) => note.kind === "other_model");
  const said = [swapped ? otherModel(swapped) : "", found ? t("jobNotes", String(found)) : ""].filter(Boolean);
  const line = row.querySelector(".job-notes");
  line.textContent = said.join(" ");
  line.hidden = !said.length;
}
