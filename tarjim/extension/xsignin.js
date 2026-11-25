// The person's own X sign-in for one download (tarjim/x_posts.py; docs/decisions.md, 2026-11-25).
// Off until they press «نزّله بدخولي في إكس» on a post X kept from tarjim and allow it in the
// browser's own question. Then, on each such press only, x.com's cookies are read and handed to
// their own tarjim for that one job; tarjim keeps them in memory for that download alone and sends
// them nowhere but X. Nothing here stores them. «وقّف» gives the permission back.
import { $ } from "./dom.js";
import { post, t } from "./shared.js";

export const X_ACCESS = { permissions: ["cookies"], origins: ["https://x.com/*"] };
const REFUSED = new Set(["x_signin", "x_account"]);
const PENDING = "xSigninFor";
const FRESH = 2 * 60 * 1000;
const SAID = { sent: "xSigninSent", none: "xSigninNone", denied: "xSigninDenied", failed: "actionFailed" };

export const xAllowed = () => chrome.permissions.contains(X_ACCESS).catch(() => false);

// Firefox with first-party isolation answers only when asked for every first party.
async function xCookies() {
  const found = await chrome.cookies.getAll({ domain: "x.com" })
    .catch(() => chrome.cookies.getAll({ domain: "x.com", firstPartyDomain: null }).catch(() => []));
  return found.map(({ name, value, domain, path, secure }) => ({ name, value, domain, path, secure }));
}

async function sendSigned(id) {
  const cookies = await xCookies();
  if (!cookies.some((cookie) => cookie.name === "auth_token")) return "none";
  return post(`/retry/${id}/x-signin`, { cookies })
    .then(() => "sent", (error) => (error.body?.error === "x_none" ? "none" : "failed"));
}

// The job waiting for the permission, taken once: by the window that asked, or by the background
// when Firefox closed the window to ask.
export async function finishPending() {
  const { [PENDING]: pending } = await chrome.storage.local.get(PENDING);
  if (!pending) return "";
  await chrome.storage.local.remove(PENDING);
  return Date.now() - pending.at < FRESH ? sendSigned(pending.id) : "";
}

// From the press itself: nothing is awaited before the browser asks.
async function signedRetry(job) {
  const noted = chrome.storage.local.set({ [PENDING]: { id: job.id, at: Date.now() } });
  const allowed = await chrome.permissions.request(X_ACCESS).catch(() => false);
  await noted;
  if (allowed) return (await finishPending()) || "sent";
  await chrome.storage.local.remove(PENDING);
  return "denied";
}

export const xSaid = (outcome) => SAID[outcome] || "";

// tell(text, kind) says the outcome on the job.
export function xSigninButtons(job, tell, refresh) {
  if (!REFUSED.has(job.error_code)) return [];
  const button = Object.assign(document.createElement("button"), { type: "button", className: "button-quiet", textContent: t("xSigninButton") });
  button.addEventListener("click", async () => {
    tell("");
    const outcome = await signedRetry(job);
    tell(t(xSaid(outcome)), outcome === "sent" || outcome === "denied" ? "" : "problem");
    if (outcome === "sent") refresh();
  });
  return [button];
}

export async function showXSignin() {
  $("x-signin").hidden = !(await xAllowed());
  $("x-signin-note").textContent = "";
  $("x-signin-stop").hidden = false;
}

async function stopXSignin() {
  await chrome.permissions.remove({ permissions: ["cookies"] }).catch(() => false);
  await chrome.permissions.remove({ origins: X_ACCESS.origins }).catch(() => false);
  const stopped = !(await xAllowed());
  $("x-signin-note").textContent = t(stopped ? "xSigninStopped" : "actionFailed");
  $("x-signin-stop").hidden = stopped;
}

export const wireXSignin = () => $("x-signin-stop").addEventListener("click", stopXSignin);
