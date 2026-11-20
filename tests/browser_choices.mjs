// Run by test_browser_choices.py: pairing.js's shareChoices and shared.js's remember against a
// browser and an engine that are not there.
let kept = {};
let engine = {};
let posted = [];
globalThis.chrome = {
  storage: { local: {
    get: async (keys) => (keys == null ? { ...kept }
      : Object.fromEntries([keys].flat().filter((k) => k in kept).map((k) => [k, kept[k]]))),
    set: async (values) => { Object.assign(kept, values); } } },
  i18n: { getMessage: (key) => key, getUILanguage: () => "ar" },
  runtime: { getURL: (path) => path },
};
globalThis.fetch = async (url, init = {}) => {
  if (url.endsWith("/browser") && init.method === "POST") posted.push(JSON.parse(init.body));
  const body = url.endsWith("/browser") ? engine : {};
  return { ok: true, status: 200, json: async () => body };
};
const pairing = await import(process.argv[2]);
const shared = await import(new URL("./shared.js", process.argv[2]).href);
const out = {};

engine = { dialect: "msa", textMode: "button", voice: "studio" };
kept = { token: "key" };
await pairing.shareChoices();
out.joined = { dialect: kept.dialect, textMode: kept.textMode, voice: kept.voice,
  shared: kept.choicesShared, posted };
posted = [];
engine = { dialect: "saudi" };
await pairing.shareChoices();
out.again = { posted };

kept = { token: "key" };
engine = {};
posted = [];
await pairing.shareChoices();
out.first = { posted };

posted = [];
await shared.remember({ voice: "eleven" });
await new Promise((done) => setTimeout(done, 20));
out.saved = posted;
posted = [];
await shared.remember({ token: "other", pairId: "x" });
await new Promise((done) => setTimeout(done, 20));
out.unshared = posted;
console.log(JSON.stringify(out));
