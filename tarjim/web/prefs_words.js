// The settings page's words and the page's tabs (2026-11-09). A setting's label, hint and choice
// names come from the interface language; the engine's Arabic label is the last fallback, so a
// setting added later is never shown as its raw key.
import { t } from "./i18n.js";

// The page's tabs, in order, and the engine's groups each one holds.
export const TABS = [
  { id: "look", groups: ["look"], preview: true },
  { id: "timing", groups: ["text", "timing"], preview: true },
  { id: "listen", groups: ["listen"] },
  { id: "translate", groups: ["translate"] },
  { id: "output", groups: ["output"] },
  { id: "dub", groups: ["dub"] },
  { id: "general", groups: [] },
];

const PERCENT = ["look.size_wide", "look.size_tall", "look.box_opacity", "look.box_padding",
  "look.outline_width", "look.shadow", "look.bottom_margin_wide", "look.bottom_margin_tall",
  "look.top_margin_wide", "look.top_margin_tall", "look.side_margin", "look.mark_size",
  "look.mark_opacity", "dub.balance"];
const SECONDS = ["timing.min_duration", "timing.max_duration", "timing.linger", "timing.min_gap",
  "timing.long_pause", "timing.join_gap", "timing.min_readable", "timing.cut_snap",
  "timing.cut_dialogue_span", "listen.chunk_seconds", "listen.gap_seconds"];
const UNITS = { "look.fade_ms": "unit_ms", "text.reading_cps": "unit_cps", "text.line_chars": "unit_chars",
  ...Object.fromEntries(PERCENT.map((key) => [key, "unit_percent"])),
  ...Object.fromEntries(SECONDS.map((key) => [key, "unit_s"])) };

function said(key, fallback = "") {
  const text = t(key);
  return text === key ? fallback : text;
}

export const label = (spec) => said(`pref_${spec.key}`, spec.label);
export const hint = (spec) => said(`hint_${spec.key}`);
export const unit = (key) => (UNITS[key] ? t(UNITS[key]) : "");

// A choice is named by its value as text: 1.0 from the engine reads as 1 here, as in the words.
export function choiceName(spec, value) {
  return said(`choice_${spec.key}_${String(value)}`, String(value).trim() || String(value));
}

export function shown(spec, value) {
  if (spec.kind === "switch") return t(value ? "prefsOn" : "prefsOff");
  if (spec.kind === "choice") return choiceName(spec, value);
  if (spec.kind === "number") return withUnit(spec.key, value);
  return `\u2066${value}\u2069`;  // a colour, font or folder reads left to right inside Arabic
}

// A percent sits on its number; any other unit after a space.
export function withUnit(key, value) {
  const named = unit(key);
  return `${value}${named === "%" ? "%" : named ? ` ${named}` : ""}`;
}
