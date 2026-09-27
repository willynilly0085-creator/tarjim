import { api, post, t } from "./shared.js";

const REASONS = { rejected: "keyRejected", shape: "keyShape" };

export const keyStatus = () => api("/keys");

export async function saveKey(provider, key) {
  const clean = key.trim();
  if (!clean) return "";
  try {
    await post("/keys", { provider, key: clean });
    return "";
  } catch (error) {
    if (error.kind !== "http") throw error;
    return t(REASONS[error.body?.result] || "keyShape");
  }
}
