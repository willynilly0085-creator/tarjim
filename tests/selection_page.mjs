// Run by test_selected_text.py: selection.js in a page that is not there.
const heard = {};
const sent = [];
const shown = [];
let picked = "some text";
let reply = { translation: "done" };
function element(tag) {
  const made = { tag, children: [], style: {}, heard: {},
    append(...kids) { made.children.push(...kids); },
    setAttribute() {}, remove() {}, attachShadow: () => made,
    addEventListener(type, handler) { made.heard[type] = handler; },
    getBoundingClientRect: () => ({ width: 100, height: 40, left: 0, top: 0, bottom: 40 }) };
  return made;
}
const range = { getBoundingClientRect: () => ({ width: 50, height: 10, left: 5, top: 5, bottom: 15 }) };
Object.assign(globalThis, { innerWidth: 800, innerHeight: 600, scrollX: 0, scrollY: 0,
  getSelection: () => ({ toString: () => picked, rangeCount: 1, getRangeAt: () => range }),
  document: { createElement: element, activeElement: null,
    documentElement: { append(host) { shown.push(host); } },
    addEventListener(type, handler) { (heard[type] ||= []).push(handler); } },
  chrome: { runtime: { onMessage: { addListener() {} },
      sendMessage: async (message) => {
        if (message.type === "tarjim-words") return null;
        sent.push(message);
        return reply;
      } },
    storage: { local: { get: async () => ({ textMode: "menu" }) },
      onChanged: { addListener(handler) { heard.changed = handler; } } } } });
await import(process.argv[2]);
const fire = (type, event) => heard[type].forEach((handler) => handler({ composedPath: () => [], ...event }));
const settled = () => new Promise((done) => setTimeout(done, 330));
const card = () => shown.at(-1).children[1];
const said = () => card().children.map((child) => child.textContent);
const out = {};

heard.changed({ textMode: { newValue: "card" } });
fire("mouseup", { isTrusted: false });
fire("keyup", { isTrusted: false, shiftKey: true });
await settled();
out.madeUp = [sent.length, shown.length];
fire("mouseup", { isTrusted: true });
await settled();
out.own = [sent.slice(), said()];

picked = "other text";
reply = { ask: true };
fire("mouseup", { isTrusted: true });
await settled();
out.held = [sent.at(-1), card().className.trim(), card().children[0].tag];
const button = card().children[0];
reply = { translation: "clicked" };
button.heard.click({ isTrusted: false });
await settled();
out.fakeClick = sent.length;
button.heard.click({ isTrusted: true });
await settled();
out.click = [sent.at(-1), said()[0]];

heard.changed({ textMode: { newValue: "button" } });
picked = "third text";
fire("mouseup", { isTrusted: true });
await settled();
out.button = [sent.length, card().className.trim()];
console.log(JSON.stringify(out));
