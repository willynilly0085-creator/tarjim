// Runs the settings page's own scripts against a pretend engine (2026-11-09) and prints what
// it sent and showed, as JSON, for tests/test_prefs_page.py.
// node prefs_page.mjs <fake_dom url> <web folder url> <words.json> <state.json> <scenario>
import { readFileSync } from "node:fs";

const [domUrl, web, wordsPath, statePath, scenario] = process.argv.slice(2);
const { install } = await import(domUrl);
const document = install();
const words = JSON.parse(readFileSync(wordsPath, "utf8"));
const start = JSON.parse(readFileSync(statePath, "utf8"));
const sent = [];
const engine = { state: structuredClone(start), save: { saved: [], refused: {}, notes: [] }, preset: null };
const wait = (ms) => new Promise((done) => setTimeout(done, ms));
const reply = (status, body) => ({ ok: status < 400, status, json: async () => body });

function route(method, path, body) {
  if (path.startsWith("/web/i18n/")) return reply(200, words);
  if (method === "GET" && path.startsWith("/prefs/fonts")) return reply(200, { fonts: ["Dubai", "Tahoma"] });
  if (method === "GET" && path.startsWith("/prefs")) return reply(200, engine.state);
  if (path === "/languages") return reply(200, [{ code: "ar", native: "العربية" }, { code: "en", native: "English" }]);
  if (path === "/setup") return reply(200, { ui_languages: [], autostart: false, auto_update: true });
  if (path === "/prefs") {
    engine.save.saved.forEach((key) => { engine.state.values[key] = body.values[key]; });
    return reply(200, engine.save);
  }
  if (path === "/prefs/reset") return reply(200, { reset: [], preset: "" });
  if (path === "/prefs/preset") return engine.preset ? engine.preset(body) : reply(200, {});
  return reply(404, { error: "path" });
}

globalThis.fetch = async (path, init = {}) => {
  const method = init.method || "GET";
  const body = init.body ? JSON.parse(init.body) : null;
  if (!path.startsWith("/web/")) sent.push([method, path, body]);
  return route(method, path, body);
};

await (await import(`${web}/i18n.js`)).load("ar");
const { openPrefs } = await import(`${web}/prefs.js`);
await openPrefs({ close() {}, engines() {}, language: async () => {} }, "ar");
const $ = (selector) => document.querySelector(selector);
const posts = () => sent.filter(([method]) => method === "POST");
const field = (key) => $(`.pref[data-key="${key}"]`);

async function autosave() {
  const range = field("look.size_wide").querySelector("input");
  range.value = "110";
  range.fire("input");
  await wait(150);
  range.value = "115";
  range.fire("input");
  await wait(200);
  const early = posts().length;
  engine.save = { saved: ["look.size_wide"], refused: {}, notes: [] };
  await wait(400);
  return { early, posts: posts(), status: $(".prefs-status").textContent, readout: field("look.size_wide").querySelector("output").textContent };
}

async function refusal() {
  engine.save = { saved: [], refused: { "look.text_colour": "«لون الكلام»: ما يبان فوق الخلفية." }, notes: [] };
  const hex = field("look.text_colour").querySelector(".pref-hex");
  hex.value = "#151413";
  hex.fire("change");
  await wait(600);
  const shown = field("look.text_colour").querySelector(".pref-refusal");
  return { posts: posts(), refusal: shown.textContent, hidden: shown.hidden, flag: field("look.text_colour").dataset.refused,
    kept: hex.value, status: $(".prefs-status").textContent };
}

async function presets() {
  engine.preset = (body) => {
    if (body.name) { engine.state = { ...engine.state, preset: body.name }; return reply(200, { used: body.name }); }
    return reply(400, { error: "هالاسم لمجموعة من ترجم نفسه، اختر اسم ثاني." });
  };
  const calm = $(".preset-row").querySelectorAll("button").find((b) => b.textContent === words.preset_calm);
  calm.click();
  await wait(50);
  const pressed = $(".preset-row").querySelectorAll("button").filter((b) => b.getAttribute("aria-pressed") === "true").map((b) => b.textContent);
  const usedStatus = $(".prefs-status").textContent;
  $(".presets-actions").querySelectorAll("button")[0].click();
  const form = $(".preset-name");
  form.querySelector("input").value = "calm";
  form.fire("submit");
  await wait(50);
  return { posts: posts(), pressed, usedStatus, refusedStatus: $(".prefs-status").textContent, formOpen: !form.hidden };
}

async function reset() {
  engine.state = { ...engine.state, changed: ["look.size_wide", "look.bold"] };
  await (await import(`${web}/prefs.js`)).reload();
  field("look.size_wide").querySelector(".pref-reset").click();
  await wait(50);
  $(".reset-tab").click();
  await wait(50);
  $(".reset-all").click();
  const question = $(".reset-sure").textContent;
  const before = posts().length;
  $(".reset-sure").querySelectorAll("button")[0].click();
  await wait(50);
  return { posts: posts(), question, before, status: $(".prefs-status").textContent };
}

const SCENARIOS = { autosave, refusal, presets, reset };
console.log(JSON.stringify(await SCENARIOS[scenario]()));
