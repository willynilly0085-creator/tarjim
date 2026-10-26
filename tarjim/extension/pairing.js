import { remember, settings, startJob } from "./shared.js";

export async function serverBase() {
  return (await settings()).server.replace(/\/+$/, "");
}

// tarjim's page, on one of its sections ("#connect" for keys); in the background when the popup
// must stay open, e.g. to keep showing a pairing code.
export async function openPage(section = "", active = true) {
  return chrome.tabs.create({ url: `${await serverBase()}/${section}`, active });
}

export async function askToPair() {
  const reply = await fetch(`${await serverBase()}/pair`, { method: "POST" }).catch(() => null);
  const asked = reply?.ok ? await reply.json() : null;
  if (asked?.id) await remember({ pairId: asked.id, pairCode: asked.code });
  return asked;
}

export async function claimPending() {
  const { pairId } = await chrome.storage.local.get("pairId");
  if (!pairId) return "none";
  const reply = await fetch(`${await serverBase()}/pair/${pairId}`).catch(() => null);
  if (!reply) return "unreachable";
  if (!reply.ok) return "waiting";
  const state = await reply.json();
  if (state.token) {
    await remember({ token: state.token, pairId: "", pairCode: "" });
    return "paired";
  }
  if (state.state === "pending") return "waiting";
  await remember({ pairId: "", pairCode: "" });
  return state.state === "denied" ? "denied" : "none";
}

// A right-click made before the extension was paired is kept and sent the moment pairing succeeds.
export async function sendWaitingJob() {
  const { waitingJob } = await chrome.storage.local.get("waitingJob");
  if (!waitingJob) return false;
  await remember({ waitingJob: null });
  await startJob(waitingJob).catch(() => null);
  return true;
}
