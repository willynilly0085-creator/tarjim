// The key field of the connect section. A key typed there is checked with the provider and saved
// by its own button, or by the page's big Save: pressing only the big one used to drop the key
// while the page said "saved".
import { post } from "./api.js";
import { t } from "./i18n.js";
import { el } from "./ui.js";

const PROBLEMS = { shape: "keyShape", rejected: "keyRejected", unreachable: "keyUnreachable" };
let shown = null;

export const typedKey = () => shown?.value.trim() || "";
export const forgetKeyForm = () => { shown = null; };

// "" when the key is saved, otherwise the words that say why not.
export async function submitKey(provider, value) {
  if (!value) return "keyShape";
  try {
    await post("/keys", { provider: provider.id, key: value });
    return "";
  } catch (error) {
    return PROBLEMS[error.body?.result] || "keyFailed";
  }
}

export function keyForm(provider, onSaved) {
  const input = el("input", { className: "text-input", type: "password", dir: "ltr", autocomplete: "off",
    spellcheck: false, placeholder: provider.has_key ? t("keySet") : "" });
  const note = el("span", { className: "meta key-state", role: "status" });
  const save = el("button", { type: "submit", className: "button-quiet", textContent: t("keySave") });
  shown = input;
  const form = el("form", { className: "key-row", noValidate: true },
    el("label", { className: "field" }, el("span", { className: "field-label", textContent: t("keyLabel") }), input),
    el("div", { className: "row" }, provider.key_url ? el("a", { className: "text-link", href: provider.key_url,
      target: "_blank", rel: "noopener noreferrer", textContent: t("getKey") }) : "", save, note));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    save.disabled = true;
    note.textContent = t("keyChecking");
    const problem = await submitKey(provider, input.value.trim());
    save.disabled = false;
    note.textContent = t(problem || "keySaved");
    if (problem) return;
    input.value = "";
    await onSaved();
    shown?.closest("form")?.querySelector(".key-state")?.replaceChildren(t("keySaved"));
  });
  return form;
}
