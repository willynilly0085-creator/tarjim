import { $, api, post } from "./api.js";
import { load } from "./i18n.js";
import { watchPairing } from "./pairing.js";
import { repaint, startWizard, wireWizard } from "./wizard.js";
import { openWorkspace } from "./workspace.js";

const guess = () => (navigator.language || "en").toLowerCase().startsWith("ar") ? "ar" : "en";

async function boot() {
  const setup = await api("/setup");
  await load(setup.ui_language || guess());
  $("ui-language").value = document.documentElement.lang;
  wireWizard();
  watchPairing();
  $("ui-language").addEventListener("change", async () => {
    await post("/setup", { ui_language: $("ui-language").value });
    await load($("ui-language").value);
    repaint();
  });
  $("open-settings").addEventListener("click", async () => {
    $("open-settings").hidden = true;
    startWizard(await api("/setup"), openWorkspace, "engine");
  });
  if (setup.setup_done === "yes") await openWorkspace();
  else startWizard(setup, openWorkspace);
}

boot();
