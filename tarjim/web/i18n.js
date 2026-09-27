let words = {};

export const t = (key, values = {}) =>
  String(words[key] ?? key).replace(/\{(\w+)\}/g, (_, name) => values[name] ?? "");

export function apply(root = document) {
  root.querySelectorAll("[data-t]").forEach((el) => { el.textContent = t(el.dataset.t); });
}

export async function load(language) {
  words = await (await fetch(`/web/i18n/${language}.json`)).json();
  document.documentElement.lang = language;
  document.documentElement.dir = words.dir || "ltr";
  apply();
}
