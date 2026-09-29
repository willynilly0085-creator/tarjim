import { t } from "./i18n.js";

const aliasName = (m) => (t(`model_${m}`) === `model_${m}` ? m : t(`model_${m}`));

export function modelLabel(source, m) {
  const name = source?.model_labels?.[m] || aliasName(m);
  return m === source?.suggested ? `${name} · ${t("modelSuggested")}` : name;
}

export function modelOptions(source, models) {
  return models.filter(Boolean).map((m) => ({ value: m, label: modelLabel(source, m), group: source?.model_groups?.[m] || "" }));
}

export function fillModels(select, options, picked, extra = []) {
  const option = (o) => new Option(o.label, o.value, false, o.value === picked);
  const grouped = options.some((o) => o.group);
  const group = (name) => Object.assign(document.createElement("optgroup"), { label: t(name) });
  if (!grouped) return select.replaceChildren(...options.map(option), ...extra);
  const latest = group("modelsLatest");
  latest.append(...options.filter((o) => o.group !== "more").map(option));
  const more = group("modelsMore");
  more.append(...options.filter((o) => o.group === "more").map(option));
  return select.replaceChildren(latest, more, ...extra);
}
