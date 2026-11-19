// Run by test_selected_text.py: textcard.js against a browser that is not there.
const kept = { server: "http://tarjim.test", token: "key", target: "ar" };
const calls = { registered: [], unregistered: 0, asked: [], woken: 0, injected: [], told: [] };
let granted = false, allow = true, answers = [];
globalThis.chrome = {
  storage: { local: {
    get: async (keys) => Object.fromEntries([keys].flat().filter((k) => k in kept).map((k) => [k, kept[k]])),
    set: async (values) => { Object.assign(kept, values); } } },
  i18n: { getMessage: (key) => `[${key}]`, getUILanguage: () => "ar" },
  permissions: { contains: async () => granted, request: async () => { granted = allow; return allow; } },
  scripting: {
    getRegisteredContentScripts: async () => calls.registered.slice(-1),
    registerContentScripts: async (scripts) => { calls.registered.push(...scripts); },
    unregisterContentScripts: async () => { calls.unregistered += 1; calls.registered = []; },
    executeScript: async (how) => { if (how.target.tabId === 9) throw new Error("no"); calls.injected.push(how); } },
  tabs: { sendMessage: async (...sent) => { calls.told.push(sent); },
    query: async () => [{ id: 1, url: "https://shop.example/item" }, { id: 2, url: "chrome://extensions/" },
      { id: 9, url: "https://refused.example/" }, { id: 3, url: "http://plain.example/" }] },
  runtime: { getURL: (path) => path,
    sendNativeMessage: async () => { calls.woken += 1; return { started: true }; } },
};
globalThis.fetch = async (url, init = {}) => {
  if (url.endsWith("/ui-language") || url.includes("_locales")) throw new TypeError("none");
  if (url.endsWith("/ping")) return { ok: true, status: 200, json: async () => ({}) };
  calls.asked.push({ url, body: init.body && JSON.parse(init.body), token: init.headers["X-Tarjim-Token"] });
  const next = answers.shift();
  if (next === "offline") throw new TypeError("offline");
  return { ok: next.status === 200, status: next.status, json: async () => next.body };
};
const card = await import(process.argv[2]);
const said = (message) => new Promise((done) => card.answer(message, null, done));
const out = {};
answers = [{ status: 200, body: { translation: "hello", by: "gemini" } }];
out.good = await said({ type: "tarjim-text", text: "selected" });
out.sent = calls.asked[0];
answers = [{ status: 502, body: { error: "failed", error_code: "quota" } }];
out.quota = await said({ type: "tarjim-text", text: "x" });
answers = [{ status: 413, body: { error: "long" } }];
out.long = await said({ type: "tarjim-text", text: "x" });
answers = [{ status: 403, body: { error: "token" } }];
out.unpaired = await said({ type: "tarjim-text", text: "x" });
answers = ["offline", { status: 200, body: { translation: "woken" } }];
out.woken = [await said({ type: "tarjim-text", text: "x" }), calls.woken];
out.words = await said({ type: "tarjim-words" });
out.other = card.answer({ type: "something else" }, null, () => {});
out.menuOnly = [await card.syncSelection(), calls.registered.length];
allow = false;
out.refused = [await card.chooseTextMode("card"), kept.textMode, calls.registered.length];
allow = true;
out.allowed = [await card.chooseTextMode("card"), kept.textMode, calls.registered.map((s) => [s.js, s.matches])];
out.back = [await card.chooseTextMode("menu"), kept.textMode, calls.unregistered];
kept.textMode = "menu";
out.updatedMenu = [await card.reachOpenPages(), calls.injected.length];
kept.textMode = "button";
granted = true;
out.updated = [await card.reachOpenPages(), calls.injected.map((how) => [how.target, how.files])];
calls.injected = [];
granted = false;
out.shown = [await card.showCard({ id: 4 }, 2, "picked"), calls.injected[0], calls.told[0]];
out.closed = await card.showCard({ id: 9 }, 0, "picked");
let clock = 1_000_000;
Date.now = () => clock;
answers = Array.from({ length: 13 }, () => ({ status: 200, body: { translation: "t" } }));
const unasked = [];
for (let i = 0; i < 11; i += 1) unasked.push(await said({ type: "tarjim-text", text: "x", auto: true }));
out.unasked = [unasked.filter((got) => got.translation).length, unasked[10]];
out.clicked = await said({ type: "tarjim-text", text: "x" });
clock += 61_000;
out.later = await said({ type: "tarjim-text", text: "x", auto: true });
console.log(JSON.stringify(out));
