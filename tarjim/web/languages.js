function inCurrent(code) {
  try {
    return new Intl.DisplayNames([document.documentElement.lang], { type: "language" }).of(code) || "";
  } catch {
    return "";
  }
}

function choice(language) {
  const label = document.createElement("label");
  label.className = "choice";
  const input = Object.assign(document.createElement("input"), { type: "radio", name: "ui", value: language.code });
  const name = Object.assign(document.createElement("span"), { className: "choice-name", textContent: language.name, lang: language.code });
  const local = inCurrent(language.code);
  const note = Object.assign(document.createElement("span"), { className: "choice-note", textContent: local === language.name ? "" : local });
  label.append(input, name, note);
  return label;
}

export function fillLanguageChoices(languages, picked) {
  const box = document.getElementById("language-choices");
  box.replaceChildren(...languages.map(choice));
  const input = box.querySelector(`input[value="${picked}"]`);
  if (input) input.checked = true;
}

export function fillLanguageMenu(languages, picked) {
  const menu = document.getElementById("ui-language");
  menu.replaceChildren(...languages.map((l) => Object.assign(new Option(l.name, l.code, false, l.code === picked), { lang: l.code })));
}

export function guessLanguage(languages) {
  const codes = new Set(languages.map((l) => l.code));
  const wanted = (navigator.languages || [navigator.language || "en"]).map((tag) => tag.toLowerCase().split("-")[0]);
  return wanted.find((code) => codes.has(code)) || "en";
}
