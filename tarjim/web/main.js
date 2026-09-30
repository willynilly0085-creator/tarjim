import { $, api, post } from "./api.js";
import { load } from "./i18n.js";
import { fillLanguageMenu, guessLanguage } from "./languages.js";
import { watchPairing } from "./pairing.js";
import { showPhone } from "./phone.js";
import { repaint, startSettings, startWizard, wireWizard } from "./wizard.js";
import { repaintAssistant, startAssistant } from "./assistant.js";
import { openWorkspace } from "./workspace.js";

async function boot() {
  const setup = await api("/setup");
  await load(setup.ui_language || guessLanguage(setup.ui_languages));
  fillLanguageMenu(setup.ui_languages, document.documentElement.lang);
  wireWizard();
  watchPairing();
  $("ui-language").addEventListener("change", async () => {
    await post("/setup", { ui_language: $("ui-language").value });
    await load($("ui-language").value);
    repaint();
    repaintAssistant();
  });
  const manual = (from) => startWizard(setup, openWorkspace, from);
  const settings = async () => {
    $("open-settings").hidden = true;
    startSettings(await api("/setup"), openWorkspace, () => startAssistant(openWorkspace, manual));
  };
  $("open-settings").addEventListener("click", settings);
  if (setup.setup_done !== "yes" || location.hash === "#setup") return startAssistant(openWorkspace, manual);
  if (location.hash !== "#phone") return openWorkspace();
  await settings();
  showPhone();
}

boot();
