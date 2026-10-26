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
// Voices that need the person's own key: offered only once it is saved (or when tarjim cannot say).
const KEYED = { "dub-gemini": "gemini", "dub-fish": "fish", "dub-fishvoice": "fish" };
let offered = "";

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

async function usable(target) {
  const voices = await api("/voices").catch(() => ({}));
  return ITEMS.map(([id]) => id).filter((id) => !(ARABIC_ONLY.has(id) && target !== "ar")
    && voices[KEYED[id]]?.has_key !== false);
}

// A key saved or removed on tarjim's page shows here on the next check.
export async function refreshMenus() {
  const { target } = await settings();
  if ((await usable(target)).join() !== offered) await buildMenus();
}

// The person's last choice sits first, one click away; every other kind waits under "Other options".
async function build() {
  const { target, mode } = await settings();
  const kinds = await usable(target);
  offered = kinds.join();
  const first = kinds.includes(mode) ? mode : "burn";
  const title = await rootTitle(target);
  await new Promise((resolve) => chrome.contextMenus.removeAll(resolve));
  await create({ id: ROOT, title, contexts: CONTEXTS });
  const key = (id) => ITEMS.find(([item]) => item === id)[1];
  await create({ id: first, parentId: ROOT, title: t(key(first)), contexts: CONTEXTS });
  await create({ id: MORE, parentId: ROOT, title: t("menuMore"), contexts: CONTEXTS });
  for (const id of kinds.filter((kind) => kind !== first)) {
    await create({ id, parentId: MORE, title: t(key(id)), contexts: CONTEXTS });
  }
  await create({ id: "tarjim-line", parentId: ROOT, type: "separator", contexts: CONTEXTS });
  await create({ id: OTHER, parentId: ROOT, title: t("menuOther"), contexts: CONTEXTS });
}

export const isMode = (id) => ITEMS.some(([mode]) => mode === id);
