// The live preview (2026-11-09): a frame drawn with CSS from the same values the burn uses, so
// size, colours, box, outline, margins, mark and fade change as the person moves a control.
// It warns when a full line would not fit the frame's width and become a third line, and
// "شوف الشكل الحقيقي" asks the engine for one frame drawn by libass itself, the burn's own way.
import { t } from "./i18n.js";
import { el } from "./ui.js";

// The burn's sample lines (render/preview.py SAMPLES): two speakers, one shared subtitle.
const SAMPLES = { ar: ["وش رايك نروح البحر بكرة الصبح؟", "فكرة حلوة، بس بدري"],
  en: ["Shall we go to the beach tomorrow morning?", "Sounds good, but early"] };
const FONT = { wide: 0.058, tall: 0.066 };  // prefs/table_look LANDSCAPE_FONT, PORTRAIT_FONT
const REPLAY_AFTER = 250;
const EIGHT = [[1, 0], [-1, 0], [0, 1], [0, -1], [0.7, 0.7], [-0.7, 0.7], [0.7, -0.7], [-0.7, -0.7]];

const sample = (language) => SAMPLES[language] || SAMPLES.en;
const heights = new Map();

// libass sizes a font by its whole line height (ascent and descent), CSS by its em: a font
// whose line is 1.7 em tall is drawn 1.7 times smaller by the burn than by the same CSS size.
export function lineHeightOf(font, weight) {
  const key = `${weight} ${font}`;
  if (!heights.has(key)) {
    const pen = document.createElement("canvas").getContext?.("2d");
    if (pen) pen.font = `${weight} 100px "${font}"`;
    const m = pen?.measureText("Hg");
    const tall = m ? (m.fontBoundingBoxAscent + m.fontBoundingBoxDescent) / 100 : 0;
    heights.set(key, tall > 0.5 ? tall : 1);
  }
  return heights.get(key);
}

export function rgba(hex, opacity) {
  const n = Number.parseInt(String(hex).replace("#", ""), 16) || 0;
  return `rgb(${(n >> 16) & 255} ${(n >> 8) & 255} ${n & 255} / ${opacity}%)`;
}

// Outlined letters: libass draws the edge all round each letter, so eight shadows make it here.
export function outline(v) {
  const width = (v["look.outline_width"] / 100).toFixed(3);
  const blur = (v["look.soft_edge"] * 0.02).toFixed(3);
  const edge = EIGHT.map(([x, y]) => `${(x * width).toFixed(3)}em ${(y * width).toFixed(3)}em ${blur}em ${v["look.outline_colour"]}`);
  return [...edge, `0.05em 0.07em 0.08em rgb(0 0 0 / ${v["look.shadow"]}%)`].join(", ");
}

// The frame's CSS from the values; shape is "wide" or "tall".
export function looks(v, shape) {
  const box = v["look.style"] === "box";
  const top = v["look.position"] === "top";
  const margin = v[`look.${top ? "top" : "bottom"}_margin_${shape}`];
  return {
    "--font-ratio": String(FONT[shape] * v[`look.size_${shape}`] / 100 / lineHeightOf(v["look.font"], v["look.bold"] ? 700 : 400)),
    "--text": v["look.text_colour"],
    "--box": box ? rgba(v["look.box_colour"], v["look.box_opacity"]) : "transparent",
    "--pad": box ? `${v["look.box_padding"] / 100}em` : "0",
    "--edge": box ? "none" : outline(v),
    "--weight": v["look.bold"] ? "700" : "400",
    "--face": `"${v["look.font"]}", system-ui, sans-serif`,
    "--side": `${v["look.side_margin"]}%`,
    "--top": top ? `${margin}%` : "auto",
    "--bottom": top ? "auto" : `${margin}%`,
    "--fade": `${v["look.fade_ms"]}ms`,
    "--mark-size": `${v["look.mark_size"]}`,
    "--mark-opacity": String(v["look.mark_opacity"] / 100),
  };
}

function lines(v, language) {
  const two = v["timing.dialogue_cues"] !== false;
  const dash = two ? v["look.dialogue_dash"] : "";
  const other = v["look.speaker_colours"] ? String(v["look.speaker_palette"]).split(",")[0] : v["look.text_colour"];
  const [first, second] = sample(language);
  const a = el("span", { className: "preview-line", textContent: `${dash}${first}` });
  const b = el("span", { className: "preview-line second", textContent: `${dash}${second}` });
  b.style.color = other;
  b.dataset.staged = String(Boolean(two && v["look.staged_reveal"]));
  return [a, b];
}

// A line as long as the longest the translation may write, in the frame's own font and size.
function probeText(language, letters) {
  const words = sample(language).join(" ");
  return words.repeat(Math.ceil(letters / words.length) + 1).slice(0, letters);
}

function wraps(frame, probe, v) {
  if (typeof frame.getBoundingClientRect !== "function") return false;
  const width = frame.getBoundingClientRect().width;
  const room = width * (1 - (2 * v["look.side_margin"]) / 100);
  const pad = v["look.style"] === "box" ? (2 * v["look.box_padding"]) / 100 : 0;
  const size = Number.parseFloat(getComputedStyle(probe).fontSize) || 0;
  return width > 0 && probe.getBoundingClientRect().width > room - pad * size;
}

export function makePreview({ real }) {
  const state = { shape: "wide", values: null, language: "ar", replay: 0 };
  const frame = el("div", { className: "preview-frame" });
  const sub = el("p", { className: "preview-sub" });
  const probe = el("span", { className: "preview-probe" });
  probe.setAttribute("aria-hidden", "true");
  const mark = el("img", { className: "preview-mark", src: "/web/icon.svg", alt: "" });
  frame.append(mark, sub, probe);
  const warn = el("p", { className: "preview-warn", role: "status" });
  const picture = el("img", { className: "preview-picture", alt: "", hidden: true });
  const caption = el("p", { className: "meta preview-caption", role: "status" });
  const shut = el("button", { type: "button", className: "button-quiet", textContent: t("prefsRealClose") });
  const figure = el("div", { className: "preview-real", hidden: true }, caption, shut);
  // The real picture takes the live frame's place, so the sticky preview never outgrows the
  // window; it goes as soon as a value changes, since it no longer shows what is chosen.
  const live = (on) => { frame.hidden = !on; picture.hidden = on; figure.hidden = on; };
  const shapes = ["wide", "tall"].map((shape) => {
    const input = el("input", { type: "radio", name: "preview-shape", value: shape, checked: shape === "wide" });
    input.addEventListener("change", () => { state.shape = shape; draw(state.values, state.language); });
    return el("label", {}, input, el("span", { textContent: t(shape === "wide" ? "prefsWide" : "prefsTall") }));
  });
  const ask = el("button", { type: "button", className: "button-quiet preview-ask", textContent: t("prefsRealLook") });

  function replay() {
    clearTimeout(state.replay);
    state.replay = setTimeout(() => {
      sub.classList.remove("fading");
      void sub.offsetWidth;  // a new animation each time, not the one already run
      sub.classList.add("fading");
    }, REPLAY_AFTER);
  }

  function draw(values, language) {
    if (!values) return;
    const drawn = JSON.stringify([values, language, state.shape]);
    if (drawn !== state.drawn && frame.hidden) live(true);
    state.drawn = drawn;
    Object.assign(state, { values, language });
    frame.dataset.shape = state.shape;
    Object.entries(looks(values, state.shape)).forEach(([name, value]) => frame.style.setProperty(name, value));
    mark.hidden = !values["look.mark"];
    frame.dataset.markSide = values["look.mark_side"];
    sub.replaceChildren(el("span", { className: "preview-box" }, lines(values, language)));
    probe.textContent = probeText(language, values["text.line_chars"]);
    const broken = wraps(frame, probe, values);
    warn.textContent = broken ? t(state.shape === "wide" ? "prefsWrapsWide" : "prefsWrapsTall", { n: values["text.line_chars"] }) : "";
    warn.hidden = !broken;
    warn.classList.toggle("quiet", state.shape === "tall");
    replay();
  }

  async function show() {
    ask.disabled = true;
    Object.assign(caption, { textContent: t("prefsRealLoading") });
    figure.hidden = false;
    try {
      const made = await real(state.shape === "tall");
      Object.assign(picture, { src: made.image, alt: t("prefsPreview") });
      picture.dataset.shape = state.shape;
      live(false);
      const font = `${String.fromCharCode(0x2066)}${made.font || state.values["look.font"]}${String.fromCharCode(0x2069)}`;
      const said = [t("prefsRealFont", { font })];
      if (made.wraps) said.push(t("prefsRealWraps"));
      caption.textContent = [...said, ...Object.values(made.refused || {})].join("\n");
    } catch (error) {
      caption.textContent = t(error?.body?.error === "ffmpeg" ? "prefsRealNoFfmpeg" : "prefsRealFailed");
    } finally {
      ask.disabled = false;
    }
  }

  ask.addEventListener("click", show);
  shut.addEventListener("click", () => { live(true); ask.focus(); });
  const choices = el("div", { className: "segments preview-shape" }, shapes);
  choices.setAttribute("role", "radiogroup");
  choices.setAttribute("aria-label", t("prefsPreview"));
  const node = el("section", { className: "preview" },
    el("div", { className: "preview-stage" }, frame, picture),
    el("div", { className: "preview-bar" }, choices, ask), warn, figure);
  node.setAttribute("aria-label", t("prefsPreview"));
  return { node, draw };
}
