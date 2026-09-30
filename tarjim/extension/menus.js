import { api, settings, t } from "./shared.js";

export const ROOT = "tarjim";
export const OTHER = "tarjim-other";
const MORE = "tarjim-more";
export const CONTEXTS = ["link", "video", "audio", "page"];
const ITEMS = [
  ["srt", "menuSrt"],
  ["burn", "menuBurn"],
  ["dub-gemini", "menuDubNatural"],
  ["dub-clone", "menuDubClone"],
  ["dub-fish", "menuDubFish"],
  ["dub-fishvoice", "menuDubNarrator"],
  ["dub-studio", "menuDubStudio"],
];
const ARABIC_ONLY = new Set(["dub-fishvoice"]);

async function languageName(code) {
  const languages = await api("/languages").catch(() => []);
  return languages.find((l) => l.code === code)?.native || code;
}

async function rootTitle(target) {
  return target === "ar" ? t("menuRootArabic") : t("menuRootTo", await languageName(target));
}

const create = (props) => new Promise((resolve) => chrome.contextMenus.create(props, () => {
  void chrome.runtime.lastError;
  resolve();
}));
let building = Promise.resolve();

export function buildMenus() {
  building = building.then(build, build);
  return building;
}

// The person's last choice sits first, one click away; every other kind waits under "Other options".
function favourite(mode, target) {
  const usable = ITEMS.some(([id]) => id === mode) && !(ARABIC_ONLY.has(mode) && target !== "ar");
  return usable ? mode : "burn";
}

async function build() {
  const { target, mode } = await settings();
  const first = favourite(mode, target);
  const title = await rootTitle(target);
  await new Promise((resolve) => chrome.contextMenus.removeAll(resolve));
  await create({ id: ROOT, title, contexts: CONTEXTS });
  const key = (id) => ITEMS.find(([item]) => item === id)[1];
  await create({ id: first, parentId: ROOT, title: t(key(first)), contexts: CONTEXTS });
  await create({ id: MORE, parentId: ROOT, title: t("menuMore"), contexts: CONTEXTS });
  for (const [id, words] of ITEMS) {
    if (id === first || (ARABIC_ONLY.has(id) && target !== "ar")) continue;
    await create({ id, parentId: MORE, title: t(words), contexts: CONTEXTS });
  }
  await create({ id: "tarjim-line", parentId: ROOT, type: "separator", contexts: CONTEXTS });
  await create({ id: OTHER, parentId: ROOT, title: t("menuOther"), contexts: CONTEXTS });
}

export const isMode = (id) => ITEMS.some(([mode]) => mode === id);
