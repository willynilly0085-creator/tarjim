import { $, api, post } from "./api.js";
import { t } from "./i18n.js";
import { el, status } from "./ui.js";

// Services with an engine of their own, then the ones the engine names, then any other address.
const OWN = { gemini: ["Google Gemini", "https://aistudio.google.com/apikey"],
  eleven: ["ElevenLabs", "https://elevenlabs.io/app/settings/api-keys"],
  fish: ["Fish Audio", "https://fish.audio/app/api-keys/"] };
const HINTS = { gemini: "voiceGeminiHint", eleven: "voiceElevenHint", fish: "voiceFishHint" };
const CUSTOM = "custom";
let view = { gemini: {}, fish: {}, eleven: { voices: [] }, speech: { presets: [] } };
let opened = "";

export const linkedVoices = () => [
  ...(view.eleven.has_key ? ["eleven", "elevenclone"] : []), ...(view.speech.has_key ? ["speech"] : [])];
export const speechName = () => view.speech.name || "";

export async function loadVoices() {
  view = await api("/voices").catch(() => view);
  return view;
}

const field = (label, control, hint = "") => el("label", { className: "field" },
  el("span", { className: "field-label", textContent: label }), control,
  hint ? el("span", { className: "meta", textContent: hint }) : "");

const text = (value = "", placeholder = "", type = "text") => el("input", {
  className: "text-input", type, dir: "ltr", autocomplete: "off", spellcheck: false, value, placeholder });

function keyForm(provider, saved, done, before = async () => {}) {
  const input = text("", saved ? t("keySet") : "", "password");
  const note = status();
  const form = el("form", { className: "stack voice-form", noValidate: true }, field(t("keyLabel"), input),
    el("button", { type: "submit", className: "button-quiet", textContent: t("keySave") }), note);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    note.textContent = t("keyChecking");
    try {
      await before();
      await post("/keys", { provider, key: input.value.trim() });
    } catch (error) {
      note.textContent = t(error.body?.error === "speech" ? "voiceSpeechBad"
        : error.body?.result === "rejected" ? "keyRejected" : "keyShape");
      return;
    }
    await loadVoices();
    done();
  });
  return form;
}

const keyLink = (name, address) => el("a", { className: "text-link", href: address, target: "_blank",
  rel: "noopener noreferrer", textContent: t("voiceGetKey", { name }) });

function elevenExtra() {
  const { has_key: linked, voices = [], voice } = view.eleven;
  if (!linked) return "";
  const pick = el("select", { className: "select" }, new Option(t("voiceAny"), ""),
    ...voices.map((v) => new Option(v.name, v.id, false, v.id === voice)));
  pick.addEventListener("change", async () => { view = await post("/voices/eleven", { voice: pick.value }); });
  return field(t("voicePreferred"), pick, t("voicePreferredHint"));
}

function ownPart(id, repaint) {
  return [keyLink(...OWN[id]), keyForm(id, view[id].has_key, repaint), id === "eleven" ? elevenExtra() : ""];
}

function speechPart(preset, repaint) {
  const { url, model, voices, has_key: linked } = view.speech;
  const same = view.speech.preset === preset;
  const other = preset === CUSTOM;
  const [address, name, names] = [text(same ? url : "", "https://"), text(same ? model : ""), text(same ? voices : "")];
  const body = () => ({ preset, url: address.value, model: name.value, voices: names.value });
  const note = status();
  const save = el("button", { type: "button", className: "button-quiet", textContent: t("voiceSpeechSave") });
  save.addEventListener("click", async () => {
    try {
      view = await post("/voices/speech", body());
      note.textContent = t("saved");
    } catch {
      note.textContent = t("voiceSpeechBad");
    }
  });
  const known = view.speech.presets.find((p) => p.id === preset);
  return [known?.keys ? keyLink(known.name, known.keys) : "",
    keyForm("speech", linked && same, repaint, () => post("/voices/speech", body())),
    other ? field(t("voiceAddress"), address) : "",
    field(t("modelLabel"), name, other ? "" : t("voiceAutoHint")),
    field(t("voiceNames"), names, t(other ? "voiceNamesHint" : "voiceAutoHint")), save, note];
}

function hint(chosen) {
  if (chosen === "none") return t("voiceNoneHint");
  if (chosen === CUSTOM) return t("voiceOtherHint");
  if (OWN[chosen]) return t(HINTS[chosen]);
  const found = view.speech.presets.find((p) => p.id === chosen);
  const speaks = found.languages.length ? ` ${t("voiceSpeaks", { languages: found.languages.join(", ") })}` : "";
  return `${t("voicePresetHint", { name: found.name })}${speaks}`;
}

function linkedNow() {
  if (view.speech.has_key) return view.speech.preset;
  return ["eleven", "fish", "gemini"].find((id) => view[id].has_key) || "none";
}

export function voicePanel(repaint) {
  const chosen = opened || linkedNow();
  const names = [["none", t("voiceServiceNone")], ...Object.entries(OWN).map(([id, [name]]) => [id, name]),
    ...view.speech.presets.map((p) => [p.id, p.name]), [CUSTOM, t("voiceServiceOther")]];
  const service = el("select", { className: "select" },
    ...names.map(([id, name]) => new Option(name, id, false, id === chosen)));
  service.addEventListener("change", () => { opened = service.value; repaint(); });
  const part = chosen === "none" ? [] : OWN[chosen] ? ownPart(chosen, repaint) : speechPart(chosen, repaint);
  return el("div", { className: "stack voice-link" }, field(t("voiceService"), service, hint(chosen)), ...part);
}

export async function renderVoices() {
  await loadVoices();
  const paint = () => $("voice-body").replaceChildren(voicePanel(paint));
  paint();
}
