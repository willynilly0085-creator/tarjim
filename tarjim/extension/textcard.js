// The background's side of "translate the selected text": puts selection.js into the page, and
// answers it with the translation from the person's own tarjim (POST /text) or the reason in
// their words. The page never talks to tarjim itself, and never holds the pairing key.
import { ApiError, errorLabel, loadWords, post, remember, settings, t, uiDirection, wakeEngine } from "./shared.js";

export const TEXT = "tarjim-text";
const SCRIPT = { id: "tarjim-selection", js: ["selection.js"], matches: ["<all_urls>"], runAt: "document_idle", allFrames: true };
const EVERYWHERE = { origins: ["<all_urls>"] };
const NOT_REACHED = { offline: "offlineTitle", token: "pairTitle" };

export const watchesPages = (mode) => mode === "button" || mode === "card";

// Registered scripts are dropped when the extension is updated: put back at every start. A
// choice of "as I select" the person then did not allow goes back to the menu.
export async function syncSelection() {
  const { textMode } = await settings();
  const wanted = watchesPages(textMode) && await chrome.permissions.contains(EVERYWHERE);
  if (watchesPages(textMode) && !wanted) await remember({ textMode: "menu" });
  const have = await chrome.scripting.getRegisteredContentScripts({ ids: [SCRIPT.id] }).catch(() => []);
  if (wanted && !have.length) await chrome.scripting.registerContentScripts([SCRIPT]);
  if (!wanted && have.length) await chrome.scripting.unregisterContentScripts({ ids: [SCRIPT.id] });
  return wanted;
}

// From a click in the settings, so the browser may ask the person: nothing is awaited before
// the asking. Firefox closes the popup while it asks, so the choice is saved first and the
// background finishes the work when the permission arrives (background.js).
export async function chooseTextMode(mode) {
  const saved = remember({ textMode: mode });
  const allowed = !watchesPages(mode) || await chrome.permissions.request(EVERYWHERE).catch(() => false);
  await saved;
  await syncSelection();
  return allowed;
}

function reason(error) {
  if (!(error instanceof ApiError)) return t("errUnknown");
  if (error.kind !== "http") return t(NOT_REACHED[error.kind]);
  if (error.body?.error === "long") return t("textLong");
  return errorLabel({ error_code: error.body?.error_code });
}

// A stopped engine is started once (native messaging) before the selection is given up.
async function translation(text) {
  const { target, textOther } = await settings();
  const ask = () => post("/text", { text, target, other: textOther });
  try {
    const first = await ask().catch(async (error) => {
      if (error.kind !== "offline" || !(await wakeEngine(30))) throw error;
      return ask();
    });
    return { translation: first.translation };
  } catch (error) {
    return { message: reason(error) };
  }
}

// "The card right away" asks with no click, and a page can steer what is selected when the
// person clicks: past a few such translations a minute the card offers its button instead, so
// no page can spend the person's translations faster than that. A click is never held back.
const AUTO = { most: 10, within: 60_000 };
let unasked = [];
function tooMany() {
  const now = Date.now();
  unasked = unasked.filter((at) => now - at < AUTO.within);
  if (unasked.length >= AUTO.most) return true;
  unasked.push(now);
  return false;
}

const cardWords = () => ({ working: t("textWorking"), copy: t("copy"), copied: t("copied"),
  ask: t("textAsk"), long: t("textLong"), dir: uiDirection() });

export function answer(message, _sender, respond) {
  if (message?.type === "tarjim-words") loadWords().then(() => respond(cardWords()));
  else if (message?.type === "tarjim-text") loadWords().then(() => (message.auto && tooMany() ? { ask: true } : translation(String(message.text || "")))).then(respond);
  else return false;
  return true;
}

// False where the browser lets no extension in (its own pages, the add-ons shop).
export async function showCard(tab, frameId, text) {
  const frame = frameId ?? 0;
  try {
    await chrome.scripting.executeScript({ target: { tabId: tab.id, frameIds: [frame] }, files: ["selection.js"] });
    await chrome.tabs.sendMessage(tab.id, { type: "tarjim-selection", text: text || "" }, { frameId: frame });
    return true;
  } catch {
    return false;
  }
}
