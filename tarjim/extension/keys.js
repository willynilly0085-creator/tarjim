import { $ } from "./dom.js";
import { api, post, t } from "./shared.js";

const REASONS = { rejected: "keyRejected", shape: "keyShape", unreachable: "keyUnreachable" };
const FALLBACK_VOICE = "studio";  // needs no key and no strong computer

export const keyStatus = () => api("/keys");

// Voices that need a key the person has not saved stay listed, marked and not pickable; when tarjim
// cannot be asked, they stay as they are.
function markKeyed(select, view) {
  let missing = false;
  select.querySelectorAll("[data-key]").forEach((option) => {
    const ready = view[option.dataset.key]?.has_key !== false;
    option.disabled = !ready;
    option.textContent = ready ? t(option.dataset.i18n) : `${t(option.dataset.i18n)} · ${t("needsKey")}`;
    missing ||= !ready;
  });
  return missing;
}

// Voices from a service the person linked on tarjim's page appear once its key is saved.
export async function showLinkedVoices(select) {
  const view = await api("/voices").catch(() => ({}));
  select.querySelectorAll("[data-linked]").forEach((option) => {
    option.hidden = !view[option.dataset.linked]?.has_key;
  });
  $("voice-keys").hidden = !markKeyed(select, view);
  const chosen = select.selectedOptions[0];
  if (!chosen || chosen.hidden || chosen.disabled) select.value = FALLBACK_VOICE;
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
