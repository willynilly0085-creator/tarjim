import { $, api, post } from "./api.js";
import { t } from "./i18n.js";
import { button, copyText, el, selectText, status } from "./ui.js";
import { linkedVoices, loadVoices } from "./voices.js";

const WATCH_MS = 3000;
const BOTFATHER = "https://t.me/BotFather";
const MODES = ["burn", "srt", "dub-gemini", "dub-clone", "dub-studio"];
const VOICE = { "dub-gemini": "voiceNatural", "dub-clone": "voiceClone", "dub-studio": "voiceStudio",
  "dub-eleven": "voiceEleven", "dub-elevenclone": "voiceElevenClone", "dub-speech": "voiceSpeech" };
const offered = () => [...MODES, ...linkedVoices().map((voice) => `dub-${voice}`)];
let watching = 0;

const modeName = (mode) => (VOICE[mode] ? `${t("outputDub")} · ${t(VOICE[mode])}` : t(mode === "srt" ? "outputSrt" : "outputBurn"));

function paintProblem(view) {
  return view.problem ? el("p", { className: "error", role: "alert", textContent: t(`phoneProblem_${view.problem}`) }) : "";
}

function connectForm() {
  const token = el("input", { className: "text-input", id: "phone-token", type: "password", dir: "ltr",
    autocomplete: "off", spellcheck: false });
  const note = status();
  const go = button(t("phoneConnect"), async () => {
    go.disabled = true;
    note.textContent = t("phoneChecking");
    const reply = await post("/phone/connect", { token: token.value.trim() }).catch((error) => error.body || {});
    go.disabled = false;
    if (reply.error) { note.textContent = t(`phoneError_${reply.error}`); note.className = "meta error"; return; }
    paint(reply);
  }, "primary");
  return el("ol", { className: "how" },
    el("li", {}, el("span", { textContent: t("phoneStep1") }), " ",
      el("a", { className: "text-link", href: BOTFATHER, target: "_blank", rel: "noopener", textContent: t("phoneOpenBotFather") })),
    el("li", {}, el("span", { textContent: t("phoneStep2") }),
      el("div", { className: "key-row phone-token" }, el("label", { className: "field-label", htmlFor: "phone-token", textContent: t("phoneTokenLabel") }),
        el("div", { className: "row" }, token, go), note)));
}

function pairing(view) {
  const address = el("code", { className: "command", dir: "ltr", textContent: view.link });
  const copy = button(t("copy"), async () => {
    if (await copyText(view.link)) copy.textContent = t("copied");
    else selectText(address);
  });
  return el("div", { className: "phone-pair" },
    el("img", { className: "qr", src: view.qr, alt: t("phoneQrAlt"), width: 180, height: 180 }),
    el("div", { className: "stack" }, el("p", { textContent: t("phoneScan") }),
      el("span", { className: "path-row" }, address, copy),
      status(t("phoneWaiting")),
      el("div", { className: "row" }, button(t("phoneNewCode"), async () => paint(await post("/phone/link", {}))),
        button(t("phoneForget"), forget))));
}

function choice(label, options, value, name) {
  const select = el("select", { className: "select" },
    ...options.map(([code, text]) => new Option(text, code, false, code === value)));
  select.addEventListener("change", async () => {
    const view = await post("/phone/choices", { [name]: select.value });
    $("phone-saved").textContent = t("saved");
    if (name === "target") paint(view);
  });
  return el("label", { className: "field" }, el("span", { className: "field-label", textContent: label }), select);
}

async function paired(view) {
  const languages = await api("/languages").catch(() => []);
  const arabic = view.target === "ar";
  return el("div", { className: "stack phone-paired" },
    el("p", { className: "meta ok", textContent: t("phonePaired", { bot: `\u2066@${view.bot}\u2069` }) }),
    choice(t("phoneTarget"), languages.map((l) => [l.code, l.native]), view.target, "target"),
    choice(t("phoneResult"), offered().map((m) => [m, modeName(m)]), view.mode, "mode"),
    arabic ? choice(t("dialect"), [["saudi", t("dialectSaudi")], ["msa", t("dialectMsa")]], view.dialect, "dialect") : "",
    el("p", { className: "meta", id: "phone-saved", role: "status" }),
    el("p", { className: "meta", textContent: t("phoneOnlyWhenOn") }),
    button(t("phoneForget"), forget));
}

async function forget() {
  paint(await post("/phone/forget", {}));
}

async function paint(view) {
  clearTimeout(watching);
  const body = !view.bot ? connectForm() : view.paired ? await paired(view) : view.link ? pairing(view) : "";
  if (view.bot && !view.paired && !view.link) return paint(await post("/phone/link", {}));
  $("phone-body").replaceChildren(paintProblem(view), body);
  if (view.bot && !view.paired) watching = setTimeout(watch, WATCH_MS);
}

async function watch() {
  if ($("phone-body").closest(".step:not(.current)") || $("wizard").hidden) return;
  const view = await api("/phone").catch(() => null);
  if (view?.paired) paint(view);
  else watching = setTimeout(watch, WATCH_MS);
}

export async function renderPhone() {
  await loadVoices();
  paint(await api("/phone").catch(() => ({ bot: "" })));
}

export function showPhone() {
  const section = document.querySelector('[data-step="phone"]');
  section.scrollIntoView({ block: "start" });
  section.querySelector("h1").tabIndex = -1;
  section.querySelector("h1").focus({ preventScroll: true });
}
