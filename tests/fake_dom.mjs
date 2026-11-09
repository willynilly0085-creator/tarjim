// A small stand-in for the browser's document (2026-11-09), enough for the settings page's
// scripts to run under node: elements, text, attributes, data-*, events that bubble, and
// selectors made of a tag, an id, classes and [attribute="value"], joined by spaces.
const camel = (name) => name.replace(/-([a-z])/g, (_, c) => c.toUpperCase());

class Node {
  constructor(tag) {
    Object.assign(this, { tagName: tag.toUpperCase(), children: [], parentNode: null, attributes: {},
      dataset: {}, listeners: {}, hidden: false, disabled: false, value: "", checked: false });
    this.style = { setProperty: (name, value) => { this.style[name] = value; } };
    this.classList = {
      set: new Set(),
      add: (...names) => names.forEach((n) => this.classList.set.add(n)),
      remove: (...names) => names.forEach((n) => this.classList.set.delete(n)),
      toggle: (n, on = !this.classList.set.has(n)) => { if (on) this.classList.set.add(n); else this.classList.set.delete(n); return on; },
      contains: (n) => this.classList.set.has(n),
    };
  }
  get className() { return [...this.classList.set].join(" "); }
  set className(text) { this.classList.set = new Set(String(text).split(/\s+/).filter(Boolean)); }
  get textContent() { return this.children.map((c) => (typeof c === "string" ? c : c.textContent)).join(""); }
  set textContent(text) { this.replaceChildren(String(text ?? "")); }
  get firstChild() { return this.children[0]; }
  get lastChild() { return this.children.at(-1); }
  get options() { return this.children.filter((c) => c.tagName === "OPTION"); }
  get selectedOptions() { return this.options.filter((o) => o.selected); }
  adopt(child) {
    if (typeof child !== "string") { child.remove(); child.parentNode = this; }
    return child;
  }
  append(...items) { items.flat().forEach((c) => this.children.push(this.adopt(c))); }
  prepend(...items) { this.children.unshift(...items.flat().map((c) => this.adopt(c))); }
  before(node) { const at = this.parentNode.children.indexOf(this); this.parentNode.children.splice(at, 0, this.parentNode.adopt(node)); }
  replaceChildren(...items) { this.children.forEach((c) => { if (typeof c !== "string") c.parentNode = null; }); this.children = []; this.append(...items); }
  remove() { if (this.parentNode) this.parentNode.children = this.parentNode.children.filter((c) => c !== this); this.parentNode = null; }
  setAttribute(name, value) {
    if (name.startsWith("data-")) this.dataset[camel(name.slice(5))] = String(value);
    else this.attributes[name] = String(value);
  }
  getAttribute(name) {
    if (name.startsWith("data-")) return this.dataset[camel(name.slice(5))] ?? null;
    if (name === "id") return this.id ?? null;
    return this.attributes[name] ?? this[name] ?? null;
  }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  dispatchEvent(event) {
    event.target ||= this;
    for (let node = this; node; node = node.parentNode) {
      (node.listeners[event.type] || []).forEach((fn) => fn(event));
      if (typeof node[`on${event.type}`] === "function") node[`on${event.type}`](event);
    }
  }
  fire(type, more = {}) { this.dispatchEvent({ type, preventDefault() {}, ...more }); }
  click() { if (!this.disabled) this.fire("click"); }
  focus() { this.ownerDocument && (this.ownerDocument.activeElement = this); }
  *walk() { for (const c of this.children) if (typeof c !== "string") { yield c; yield* c.walk(); } }
  querySelectorAll(selector) { return [...this.walk()].filter((n) => matches(n, selector, this)); }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}

class Select extends Node {
  get value() { return this.selectedOptions[0]?.value ?? this.options[0]?.value ?? ""; }
  set value(v) { this.options.forEach((o) => { o.selected = o.value === String(v); }); }
}

function one(node, part) {
  const bare = part.replace(/\[[^\]]*\]/g, "");
  const tag = bare.match(/^[a-z][\w-]*/i)?.[0];
  if (tag && node.tagName !== tag.toUpperCase()) return false;
  for (const [, id] of bare.matchAll(/#([\w-]+)/g)) if (node.id !== id) return false;
  for (const [, cls] of bare.matchAll(/\.([\w-]+)/g)) if (!node.classList.contains(cls)) return false;
  for (const [, name, , , value] of part.matchAll(/\[([\w-]+)(=("?)([^\]"]*)\3)?\]/g)) {
    const have = node.getAttribute(name);
    if (have === null || have === undefined || (value !== undefined && String(have) !== value)) return false;
  }
  return true;
}

function matches(node, selector, root) {
  return selector.split(",").some((alternative) => {
    const parts = alternative.trim().match(/(?:[^\s[]+|\[[^\]]*\])+/g);
    if (!one(node, parts.at(-1))) return false;
    let at = node.parentNode;
    for (const part of parts.slice(0, -1).reverse()) {
      while (at && at !== root.parentNode && !one(at, part)) at = at.parentNode;
      if (!at) return false;
      at = at.parentNode;
    }
    return true;
  });
}

export function install() {
  const body = new Node("body");
  const document = {
    body, activeElement: null, documentElement: { lang: "ar", dir: "rtl" },
    createElement: (tag) => Object.assign(tag === "select" ? new Select(tag) : new Node(tag), { ownerDocument: document }),
    getElementById: (id) => [...body.walk()].find((n) => n.id === id) || null,
    querySelectorAll: (s) => body.querySelectorAll(s),
    querySelector: (s) => body.querySelector(s),
  };
  globalThis.document = document;
  globalThis.Option = function Option(text = "", value = "", _byDefault = false, selected = false) {
    return Object.assign(document.createElement("option"), { textContent: text, value: String(value), selected });
  };
  for (const id of ["prefs", "workspace", "wizard", "assistant", "ui-language", "target"]) {
    body.append(Object.assign(document.createElement(id === "prefs" ? "main" : "div"), { id, hidden: id !== "workspace" }));
  }
  return document;
}
