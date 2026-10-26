export function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children.flat().filter((child) => child !== "" && child !== null && child !== undefined));
  return node;
}

export const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function button(text, onClick, kind = "button-quiet") {
  return el("button", { type: "button", className: kind, textContent: text, onclick: onClick });
}

export function status(text = "", kind = "") {
  return el("p", { className: `meta ${kind}`.trim(), role: "status", textContent: text });
}

export async function copyText(text) {
  if (!text) return false;
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const area = Object.assign(document.createElement("textarea"), { value: text, readOnly: true });
    document.body.append(area);
    area.select();
    const copied = document.execCommand("copy");
    area.remove();
    return copied;
  }
}

export function selectText(node) {
  const range = document.createRange();
  range.selectNodeContents(node);
  window.getSelection().removeAllRanges();
  window.getSelection().addRange(range);
}

// Settings opened on one section, e.g. tarjim/#connect from the extension's "Add a key".
export function showSection(step) {
  const section = document.querySelector(`[data-step="${step}"]`);
  section.scrollIntoView({ block: "start" });
  section.querySelector("h1").tabIndex = -1;
  section.querySelector("h1").focus({ preventScroll: true });
}
