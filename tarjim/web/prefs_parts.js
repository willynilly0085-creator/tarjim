// The two subtitle tabs in titled parts (2026-11-25): "شكل الترجمة" was one list of 28 settings.
// Each part shows its main settings and keeps its finer ones in a fold of its own; a part with
// only finer ones is a fold under its own name. A setting no part names still shows, in a last
// part, so a setting added later is never lost.
import { t } from "./i18n.js";
import { el } from "./ui.js";

export const PARTS = {
  look: [
    { id: "text", keys: ["look.font", "look.size_wide", "look.size_tall", "look.text_colour", "look.bold"] },
    { id: "box", keys: ["look.style", "look.box_colour", "look.box_opacity", "look.box_padding",
      "look.outline_width", "look.outline_colour", "look.shadow", "look.soft_edge"] },
    { id: "place", keys: ["look.position", "look.bottom_margin_wide", "look.bottom_margin_tall",
      "look.top_margin_wide", "look.top_margin_tall", "look.side_margin", "look.fade_ms"] },
    { id: "speakers", keys: ["look.speaker_colours", "look.speaker_palette", "look.staged_reveal",
      "look.dialogue_dash"] },
    { id: "mark", keys: ["look.mark", "look.mark_size", "look.mark_opacity", "look.mark_side"] },
  ],
  timing: [
    { id: "reading", keys: ["text.reading_cps", "text.line_chars", "text.reading_warning", "text.one_line"] },
    { id: "lines", keys: ["timing.min_duration", "timing.max_duration", "timing.linger", "timing.min_gap",
      "timing.long_pause", "timing.join_gap", "timing.min_readable", "timing.dialogue_cues"] },
    { id: "cuts", keys: ["timing.end_at_cuts", "timing.cut_snap", "timing.scene_sensitivity",
      "timing.cut_dialogue_span"] },
  ],
};

// specs: the tab's settings in the engine's order; the parts keep their own order.
function split(tabId, specs) {
  const named = PARTS[tabId].map((part) => ({ id: part.id,
    specs: part.keys.map((key) => specs.find((spec) => spec.key === key)).filter(Boolean) }));
  const placed = new Set(PARTS[tabId].flatMap((part) => part.keys));
  const rest = specs.filter((spec) => !placed.has(spec.key));
  return rest.length ? [...named, { id: "more", specs: rest }] : named;
}

function fold(title, nodes, open = false) {
  return el("details", { className: "prefs-advanced part-fold", open },
    el("summary", { textContent: title }), el("div", { className: "pref-list" }, nodes));
}

// make(spec): the setting's row. Returns the parts, each a titled section.
export function parts(tabId, specs, make) {
  return split(tabId, specs).filter((part) => part.specs.length).map((part) => {
    const name = t(`part_${tabId}_${part.id}`);
    const basic = part.specs.filter((spec) => spec.tier === "basic").map(make);
    const finer = part.specs.filter((spec) => spec.tier !== "basic").map(make);
    if (!basic.length) return el("section", { className: "pref-part only-fold" }, fold(name, finer));
    return el("section", { className: "pref-part" },
      el("h3", { className: "part-title", textContent: name }),
      el("div", { className: "pref-list" }, basic),
      finer.length ? fold(t("prefsFiner"), finer) : "");
  });
}

export const hasParts = (tabId) => tabId in PARTS;
