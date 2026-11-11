import { t } from "./i18n.js";
import { copyText } from "./ui.js";

// The summary of a finished job, ready to post: a short text that fits a tweet, and a longer one
// kept folded until asked for. Each has its own Copy, so what is pasted is exactly what is shown.
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

// Painted once per text: the page asks for the jobs every two seconds, and a repaint would close
// the longer post under the reader and reset a "Copied".
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
