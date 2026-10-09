import { api, post, t } from "./shared.js";

const REASONS = { rejected: "keyRejected", shape: "keyShape" };

export const keyStatus = () => api("/keys");

// Voices from a service the person linked on tarjim's page appear once its key is saved.
export async function showLinkedVoices(select) {
  const view = await api("/voices").catch(() => ({}));
  select.querySelectorAll("[data-linked]").forEach((option) => {
    option.hidden = !view[option.dataset.linked]?.has_key;
  });
  if (select.selectedOptions[0]?.hidden) select.value = "gemini";
}

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
