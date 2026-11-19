// Run by test_selected_text.py: selection.js in a page that is not there.
const heard = {};
const sent = [];
const shown = [];
let picked = "some text";
let reply = { translation: "done" };
let stored = "menu";
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
    addEventListener(type, handler) { (heard[type] ||= []).push(handler); },
    removeEventListener(type, handler) { heard[type] = (heard[type] || []).filter((h) => h !== handler); } },
  chrome: { runtime: { id: "tarjim", onMessage: { addListener() {} },
      sendMessage: async (message) => {
        if (message.type === "tarjim-words") return null;
        sent.push(message);
        return reply;
      } },
    storage: { local: { get: async () => ({ textMode: stored }) },
      onChanged: { addListener(handler) { heard.changed = handler; } } } } });
const thrown = [];
globalThis.tarjimSelection = true;  // the mark 1.1.16 left in a page it was cut off from
process.on("unhandledRejection", (error) => thrown.push(String(error?.message || error)));
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
// The add-on was updated or turned off while this page stayed open: its script is left behind
// with no add-on to talk to, and the browser throws instead of answering.
heard.changed({ textMode: { newValue: "card" } });
stored = "card";
const before = shown.length;
chrome.runtime.id = undefined;
chrome.runtime.sendMessage = () => { throw new Error("Extension context invalidated."); };
picked = "fourth text";
fire("mouseup", { isTrusted: true });
await settled();
const listening = () => ["mouseup", "keyup", "keydown", "mousedown"].map((type) => (heard[type] || []).length);
out.orphan = [thrown, shown.length - before, listening()];
// The updated add-on puts its own copy into the same page, and that one works.
chrome.runtime.id = "tarjim";
chrome.runtime.sendMessage = async (message) => (message.type === "tarjim-words" ? null : (sent.push(message), reply));
// a second copy, as the browser would put it in (Node runs one file once, so it goes as text)
const { readFileSync } = await import("node:fs");
const again = readFileSync(new URL(process.argv[2]), "utf-8");
await import(`data:text/javascript;base64,${Buffer.from(again).toString("base64")}`);
await settled();
picked = "fifth text";
fire("mouseup", { isTrusted: true });
await settled();
out.again = [listening(), sent.at(-1)?.text, thrown];
console.log(JSON.stringify(out));
