import { post } from "./api.js";
import { t } from "./i18n.js";
import { el } from "./ui.js";

const KEY_PAGES = { gemini: "https://aistudio.google.com/apikey", openai: "https://platform.openai.com/api-keys" };

function wanted(state) {
  const { translate, listen } = state.plan;
  return [translate, listen].find((c) => KEY_PAGES[c.provider] && !c.ready)?.provider;
}

export function keyNeed(state, repaint) {
  const provider = wanted(state);
  const input = el("input", { className: "text-input", type: "password", dir: "ltr", autocomplete: "off", spellcheck: false });
  const note = el("p", { className: "meta", role: "status" });
  const form = el("form", { className: "plan-row need", noValidate: true },
    el("p", { className: "field-label", textContent: t("needTitle") }),
    el("p", { textContent: t(`need_key_${provider}`) }),
    el("a", { className: "text-link", href: KEY_PAGES[provider], target: "_blank", rel: "noopener noreferrer", textContent: t("getKeyFree") }),
    el("label", { className: "field" }, el("span", { className: "field-label", textContent: t("keyLabel") }), input),
    el("button", { type: "submit", className: "button-quiet", textContent: t("keySave") }), note);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    note.textContent = t("keyChecking");
    try {
      await post("/keys", { provider, key: input.value.trim() });
    } catch (error) {
      note.textContent = t(error.body?.result === "rejected" ? "keyRejected" : "keyShape");
      return;
    }
    state.scan.keys.saved.push(provider);
    state.apiModels = { ...state.apiModels, [provider]: await post("/connections/models", { provider }).catch(() => ({ models: [] })) };
    for (const choice of [state.plan.translate, state.plan.listen]) if (choice.provider === provider) choice.ready = true;
    repaint();
  });
  return form;
}
