import { $, api, post } from "./api.js";
import { t } from "./i18n.js";
import { el, status } from "./ui.js";

const ELEVEN_KEYS = "https://elevenlabs.io/app/settings/api-keys";
const SERVICES = [["none", "voiceServiceNone"], ["eleven", ""], ["speech", "voiceServiceOther"]];
const HINTS = { none: "voiceNoneHint", eleven: "voiceElevenHint", speech: "voiceOtherHint" };
let view = { eleven: { voices: [] }, speech: {} };
let opened = "";

export const linkedVoices = () => [
  ...(view.eleven.has_key ? ["eleven", "elevenclone"] : []), ...(view.speech.has_key ? ["speech"] : [])];

export async function loadVoices() {
  view = await api("/voices").catch(() => view);
  return view;
}

const field = (label, control, hint = "") => el("label", { className: "field" },
  el("span", { className: "field-label", textContent: label }), control,
  hint ? el("span", { className: "meta", textContent: hint }) : "");

const text = (value = "", placeholder = "", type = "text") => el("input", {
  className: "text-input", type, dir: "ltr", autocomplete: "off", spellcheck: false, value, placeholder });

function keyForm(provider, saved, done) {
  const input = text("", saved ? t("keySet") : "", "password");
  const note = status();
  const form = el("form", { className: "stack voice-form", noValidate: true }, field(t("keyLabel"), input),
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
    await loadVoices();
    done();
  });
  return form;
}

function elevenPart(repaint) {
  const { has_key: linked, voices = [], voice } = view.eleven;
  const pick = el("select", { className: "select" }, new Option(t("voiceAny"), ""),
    ...voices.map((v) => new Option(v.name, v.id, false, v.id === voice)));
  pick.addEventListener("change", async () => { view = await post("/voices/eleven", { voice: pick.value }); });
  return [el("a", { className: "text-link", href: ELEVEN_KEYS, target: "_blank", rel: "noopener noreferrer", textContent: t("voiceElevenKey") }),
    keyForm("eleven", linked, repaint),
    linked ? field(t("voicePreferred"), pick, t("voicePreferredHint")) : ""];
}

function speechPart(repaint) {
  const { url, model, voices, has_key: linked } = view.speech;
  const [address, name, names] = [text(url, "https://"), text(model), text(voices)];
  const note = status();
  const save = el("button", { type: "button", className: "button-quiet", textContent: t("voiceSpeechSave") });
  save.addEventListener("click", async () => {
    try {
      view = await post("/voices/speech", { url: address.value, model: name.value, voices: names.value });
      note.textContent = t("saved");
    } catch {
      note.textContent = t("voiceSpeechBad");
    }
  });
  return [keyForm("speech", linked, repaint), field(t("voiceAddress"), address), field(t("modelLabel"), name),
    field(t("voiceNames"), names, t("voiceNamesHint")), save, note];
}

export function voicePanel(repaint) {
  const chosen = opened || (view.eleven.has_key ? "eleven" : view.speech.has_key ? "speech" : "none");
  const service = el("select", { className: "select" },
    ...SERVICES.map(([id, key]) => new Option(key ? t(key) : "ElevenLabs", id, false, id === chosen)));
  service.addEventListener("change", () => { opened = service.value; repaint(); });
  const part = chosen === "eleven" ? elevenPart(repaint) : chosen === "speech" ? speechPart(repaint) : [];
  return el("div", { className: "stack voice-link" }, field(t("voiceService"), service, t(HINTS[chosen])), ...part);
}

export async function renderVoices() {
  await loadVoices();
  const paint = () => $("voice-body").replaceChildren(voicePanel(paint));
  paint();
}
