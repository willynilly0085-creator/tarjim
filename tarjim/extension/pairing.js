import { remember, settings } from "./shared.js";

export async function serverBase() {
  return (await settings()).server.replace(/\/+$/, "");
}

// tarjim's page, on one of its sections ("#connect" for keys); in the background when the popup
// must stay open, e.g. to keep showing that a pairing request waits.
export async function openPage(section = "", active = true) {
  return chrome.tabs.create({ url: `${await serverBase()}/${section}`, active });
}

export async function askToPair() {
  const reply = await fetch(`${await serverBase()}/pair`, { method: "POST" }).catch(() => null);
  const asked = reply?.ok ? await reply.json() : null;
  if (asked?.id) await remember({ pairId: asked.id });
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
    await remember({ token: state.token, pairId: "" });
    return "paired";
  }
  if (state.state === "pending") return "waiting";
  await remember({ pairId: "" });
  return state.state === "denied" ? "denied" : "none";
}

// Nothing writes waitingJob any more: a right-clicked link waits as pendingLink (source.js) and is
// sent from the window once its quality is picked. Kept as a no-op only because background.js and
// panels.js still call it; remove those calls and this function together.
export async function sendWaitingJob() {
  await chrome.storage.local.remove("waitingJob");  // left by an older version, never to be sent
  return false;
}
