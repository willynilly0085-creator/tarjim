// The person's last choices (language, dialect, output, voice) come back the next time the page
// opens. They are kept in this browser only; one that keeps nothing starts from the defaults.
import { $ } from "./api.js";

const KEY = "tarjim.order";

function kept() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || {};
  } catch {
    return {};
  }
}

export function remember() {
  const form = $("order");
  const choices = { target: $("target").value, dialect: form.dialect.value, mode: form.mode.value,
    voice: $("voice").value };
  try {
    localStorage.setItem(KEY, JSON.stringify(choices));
  } catch {
    // a browser that keeps nothing: the page still works, from the defaults
  }
}

export const recalledTarget = () => kept().target || "";

export function recallForm() {
  const form = $("order");
  for (const name of ["dialect", "mode"]) {
    const radio = [...form[name]].find((input) => input.value === kept()[name]);
    if (radio) radio.checked = true;
  }
}

// A voice that is gone or now needs a key is not brought back.
export function recallVoice() {
  const option = [...$("voice").options].find((o) => o.value === kept().voice);
  if (option && !option.disabled && !option.hidden) $("voice").value = option.value;
}
