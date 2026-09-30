import { post, remember, settings } from "./shared.js";

export async function serverBase() {
  return (await settings()).server.replace(/\/+$/, "");
}

export async function askToPair() {
  const reply = await fetch(`${await serverBase()}/pair`, { method: "POST" }).catch(() => null);
  const id = reply?.ok ? (await reply.json()).id : null;
  if (id) await remember({ pairId: id });
  return id;
}

export async function claimPending() {
  const { pairId } = await chrome.storage.local.get("pairId");
  if (!pairId) return "none";
  const reply = await fetch(`${await serverBase()}/pair/${pairId}`).catch(() => null);
  if (!reply?.ok) return "waiting";
  const state = await reply.json();
  if (state.token) {
    await remember({ token: state.token, pairId: "" });
    return "paired";
  }
  if (state.state === "pending") return "waiting";
  await remember({ pairId: "" });
  return state.state === "denied" ? "denied" : "none";
}

// A right-click made before the extension was paired is kept and sent the moment pairing succeeds.
export async function sendWaitingJob() {
  const { waitingJob } = await chrome.storage.local.get("waitingJob");
  if (!waitingJob) return false;
  await remember({ waitingJob: null });
  await post("/jobs", waitingJob).catch(() => null);
  return true;
}
