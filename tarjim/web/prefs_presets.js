// Ready sets and going back to the original (2026-11-09): a built-in or the person's own set is
// one press; "احفظ إعداداتي باسم…" keeps what they changed under a name; going back is one
// setting, one tab or everything, and everything asks once, saying how many settings go back.
// Each one is the engine's own route, so the chat and the page do exactly the same thing.
import { post } from "./api.js";
import { t } from "./i18n.js";
import { button, el } from "./ui.js";

const presetName = (name, own) => (own.includes(name) ? name : t(`preset_${name}`));

export const resetKeys = (keys, language) => post("/prefs/reset", { keys, language });
export const resetGroups = (groups, language) =>
  Promise.all(groups.map((group) => post("/prefs/reset", { group, language })));

// hooks: { state(), reload(), say(text) }
export function makePresets(hooks) {
  const row = el("div", { className: "preset-row" });
  row.setAttribute("role", "group");
  const own = el("details", { className: "preset-own" });
  const naming = el("form", { className: "preset-name", hidden: true });
  const sure = el("div", { className: "reset-sure", hidden: true });
  const all = button(t("prefsResetAll"), () => askAll(), "button-quiet reset-all");

  async function run(work, words) {
    try {
      const answer = await work();
      hooks.say(words(answer));
      await hooks.reload();
      return true;
    } catch (error) {
      hooks.say(error?.body?.error && error.status === 400 ? error.body.error : t("prefsFailed"));
      return false;
    }
  }

  const use = (name, ownNames) => run(() => post("/prefs/preset", { name }),
    () => t("prefsUsed", { name: presetName(name, ownNames) }));

  function chip(name, ownNames, active) {
    const chosen = button(presetName(name, ownNames), () => use(name, ownNames), "preset");
    chosen.setAttribute("aria-pressed", String(name === active));
    return chosen;
  }

  function nameForm(start, done) {
    const input = el("input", { type: "text", className: "text-input", maxLength: 40, value: start });
    input.setAttribute("aria-label", t("prefsPresetName"));
    const cancel = button(t("cancel"), () => { naming.hidden = true; });
    naming.replaceChildren(input, el("button", { type: "submit", className: "primary compact", textContent: t("prefsSave") }), cancel);
    naming.onsubmit = async (event) => {
      event.preventDefault();
      if (await done(input.value.trim())) naming.hidden = true;
    };
    naming.hidden = false;
    input.focus();
  }

  const saveAs = () => nameForm("", (name) => run(() => post("/prefs/preset", { save_as: name }),
    () => t("prefsPresetSaved", { name })));

  function ownRow(name) {
    const rename = button(t("prefsRename"), () => nameForm(name, (to) => run(
      () => post("/prefs/preset", { rename: name, to }), () => t("prefsRenamed", { name: to }))));
    const drop = button(t("prefsDelete"), () => run(() => post("/prefs/preset", { delete: name }),
      () => t("prefsDeleted", { name })));
    return el("li", {}, el("span", { className: "preset-own-name", textContent: name }), rename, drop);
  }

  // Counted from what the engine puts back in every language (2026-11-09), not only the one
  // shown: another language's own font or reading speed goes back too, and is said so.
  function askAll() {
    const { changed_all: everything = [], others } = hooks.state();
    const count = everything.length;
    if (!count) return hooks.say(t("prefsNothingChanged"));
    const yes = button(t("prefsResetAllYes"), async () => {
      sure.hidden = true;
      await run(() => post("/prefs/reset", { all: true }), () => t("prefsResetDone"));
      all.focus();
    }, "primary compact");
    const no = button(t("prefsNo"), () => { sure.hidden = true; all.focus(); });
    const elsewhere = others ? el("p", { className: "meta", textContent: t("prefsResetAllOthers") }) : "";
    sure.replaceChildren(el("p", { textContent: t("prefsResetAllSure", { n: count }) }), elsewhere, yes, no);
    sure.hidden = false;
    yes.focus();
  }

  function draw() {
    const { presets, preset } = hooks.state();
    row.replaceChildren(...presets.built_in.map((name) => chip(name, presets.own, preset)),
      ...presets.own.map((name) => chip(name, presets.own, preset)));
    row.setAttribute("aria-label", t("prefsPresets"));
    current.textContent = preset ? "" : t("prefsOwnMix");
    own.hidden = !presets.own.length;
    own.replaceChildren(el("summary", { textContent: t("prefsOwn") }), el("ul", {}, presets.own.map(ownRow)));
  }

  const current = el("span", { className: "meta preset-mix" });
  const node = el("section", { className: "presets" },
    el("div", { className: "presets-head" }, el("h2", { className: "section-title", textContent: t("prefsPresets") }), current),
    row, el("div", { className: "row presets-actions" }, button(t("prefsSaveAs"), saveAs), all),
    naming, sure, own);
  return { node, draw };
}
