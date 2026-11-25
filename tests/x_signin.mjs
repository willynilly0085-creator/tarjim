// Run by test_x_signin_addon.py: xsignin.js against a browser that is not there.
import { install } from "./fake_dom.mjs";

const document = install();
const kept = { server: "http://tarjim.test", token: "key" };
const jar = [
  { name: "auth_token", value: "secret", domain: ".x.com", path: "/", secure: true, httpOnly: true, storeId: "0" },
  { name: "ct0", value: "csrf", domain: ".x.com", path: "/", secure: true, httpOnly: false },
];
const calls = { asked: [], read: [], removed: [], sent: [] };
let granted = false, allow = true, cookies = jar;
globalThis.chrome = {
  storage: { local: {
    get: async (keys) => Object.fromEntries([keys].flat().filter((k) => k in kept).map((k) => [k, kept[k]])),
    set: async (values) => { Object.assign(kept, values); },
    remove: async (key) => { delete kept[key]; } } },
  i18n: { getMessage: (key) => `[${key}]`, getUILanguage: () => "ar" },
  permissions: {
    contains: async () => granted,
    request: async (what) => { calls.asked.push(what); granted = allow; return allow; },
    remove: async (what) => { calls.removed.push(what); if (what.permissions) granted = false; return true; } },
  cookies: { getAll: async (query) => { calls.read.push(query); return cookies; } },
};
globalThis.fetch = async (url, init = {}) => {
  calls.sent.push({ url, body: JSON.parse(init.body || "{}") });
  return { ok: true, status: 200, json: async () => ({ id: "b".repeat(12) }) };
};
const x = await import(process.argv[2]);
const job = (code) => ({ id: "a".repeat(12), error_code: code });
const notes = [];
let refreshed = 0;
const press = async (code) => {
  const [button] = x.xSigninButtons(job(code), (text, kind) => notes.push([text, kind || ""]), () => { refreshed += 1; });
  button.click();
  await new Promise((done) => setTimeout(done, 20));
  return button.textContent;
};
const out = {};
out.otherFailure = x.xSigninButtons(job("download"), () => {}, () => {}).length;
allow = false;
out.denied = [await press("x_signin"), calls.read.length, calls.sent.length, "xSigninFor" in kept, notes.at(-1)];
allow = true;
await press("x_signin");
out.sent = [calls.asked.at(-1), calls.read.slice(), calls.sent.at(-1), refreshed, notes.at(-1), "xSigninFor" in kept];
cookies = [jar[1]];
await press("x_account");
out.none = [calls.sent.length, notes.at(-1)];
kept.xSigninFor = { id: "c".repeat(12), at: Date.now() - 3 * 60 * 1000 };
out.stale = [await x.finishPending(), calls.sent.length, "xSigninFor" in kept];
for (const id of ["x-signin", "x-signin-note", "x-signin-stop"]) document.body.append(Object.assign(document.createElement("p"), { id }));
x.wireXSignin();
await x.showXSignin();
const group = document.getElementById("x-signin");
out.shown = group.hidden;
document.getElementById("x-signin-stop").click();
await new Promise((done) => setTimeout(done, 20));
out.stopped = [calls.removed, document.getElementById("x-signin-note").textContent, document.getElementById("x-signin-stop").hidden];
await x.showXSignin();
out.hiddenAfter = group.hidden;
console.log(JSON.stringify(out));
