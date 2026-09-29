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
