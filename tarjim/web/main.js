import { $, api, post } from "./api.js";
import { load } from "./i18n.js";
import { fillLanguageMenu, guessLanguage } from "./languages.js";
import { watchPairing } from "./pairing.js";
import { repaint, startSettings, startWizard, wireWizard } from "./wizard.js";
import { repaintAssistant, startAssistant } from "./assistant.js";
import { openWorkspace, repaintWorkspace } from "./workspace.js";
import { repaintQuality } from "./quality.js";
import { preferKeys } from "./connect.js";
import { leavePrefs, openPrefs, repaintPrefs } from "./prefs.js";
import { isSetup } from "./settings_nav.js";
import { repaintSetupSection, showSetupSection } from "./settings_setup.js";

// Addresses that open settings on one section: the extension links here to add a key.
const SECTIONS = { "#phone": "phone", "#connect": "connect", "#voice": "voice" };

// One settings place (2026-11-25): the settings button opens the settings page; the shared list
// beside it opens a setup section (engines, keys, tools...) in the setup's own page, and a
// section chosen while one is shown keeps what was typed there.
function settingsRoutes(speak, rescan) {
  const inSetup = () => !$("wizard").hidden && $("wizard").classList.contains("settings");
  const settings = async (section = "device", byKey = false) => {
    $("open-settings").hidden = true;
    if (!inSetup()) startSettings(await api("/setup"), openWorkspace, rescan);
    showSetupSection(section, open, byKey);
  };
  const prefs = (tab) => {
    $("open-settings").hidden = true;
    return openPrefs({ close: async () => { await leavePrefs(); openWorkspace(); }, language: speak, open },
      $("target").value || "ar", tab);
  };
  async function open(id, byKey = false) {
    if (!isSetup(id)) return prefs(id);
    await leavePrefs();
    return settings(id, byKey);
  }
  return { settings, prefs };
}

async function boot() {
  const setup = await api("/setup");
  await load(setup.ui_language || guessLanguage(setup.ui_languages));
  fillLanguageMenu(setup.ui_languages, document.documentElement.lang);
  wireWizard();
  watchPairing();
  const speak = async (code) => {
    await post("/setup", { ui_language: code });
    await load(code);
    repaint();
    repaintAssistant();
    repaintQuality();
    repaintWorkspace();
    repaintPrefs();
    repaintSetupSection();
  };
  $("ui-language").addEventListener("change", () => speak($("ui-language").value));
  const manual = (from) => startWizard(setup, openWorkspace, from);
  const { settings, prefs } = settingsRoutes(speak, () => startAssistant(openWorkspace, manual));
  $("open-settings").addEventListener("click", () => prefs());
  if (setup.setup_done !== "yes" || location.hash === "#setup") return startAssistant(openWorkspace, manual);
  if (location.hash === "#prefs") return prefs();
  const section = SECTIONS[location.hash];
  if (!section) return openWorkspace();
  if (section === "connect") preferKeys();
  await settings(section);
}

boot();
