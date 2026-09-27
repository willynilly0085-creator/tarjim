export const DEFAULTS = { server: "http://127.0.0.1:17653", token: "", target: "ar", dialect: "saudi", mode: "burn", voice: "clone" };

export const STAGES = ["downloading", "hearing", "translating", "writing", "burning", "dubbing"];
const STAGE_KEYS = {
  queued: "stageQueued", downloading: "stageDownloading", hearing: "stageHearing",
  translating: "stageTranslating", writing: "stageWriting", burning: "stageBurning", dubbing: "stageDubbing",
  done: "stageDone", failed: "stageFailed",
};
const ERROR_KEYS = { quota: "errQuota", key: "errKey", download: "errDownload", tools: "errTools", dub: "errDub" };

const RTL = new Set(["ar", "fa", "ur", "he"]);
const LOCALES = new Set(["ar", "en"]);
let words = null;
let chosen = "";

function fill(entry, subs) {
  return entry.message.replace(/\$([A-Za-z_]+)\$/g, (_, name) => {
    const slot = entry.placeholders?.[name.toLowerCase()]?.content || "$1";
    return subs[Number(slot.slice(1)) - 1] ?? "";
  });
}

export const t = (key, ...subs) =>
  (words?.[key] ? fill(words[key], subs) : chrome.i18n.getMessage(key, subs)) || key;

export const uiLanguage = () => chosen || chrome.i18n.getUILanguage().slice(0, 2);
export const uiDirection = () => (RTL.has(uiLanguage()) ? "rtl" : "ltr");

async function askLanguage() {
  const { server } = await settings();
  const reply = await fetch(`${server.replace(/\/+$/, "")}/ui-language`).catch(() => null);
  return reply?.ok ? (await reply.json()).language : "";
}

export async function loadWords() {
  const stored = (await chrome.storage.local.get("uiLanguage")).uiLanguage || "";
  const language = (await askLanguage()) || stored;
  if (!LOCALES.has(language)) return false;
  const changed = language !== chosen;
  words = await (await fetch(chrome.runtime.getURL(`_locales/${language}/messages.json`))).json();
  chosen = language;
  if (language !== stored) await chrome.storage.local.set({ uiLanguage: language });
  return changed;
}

export class ApiError extends Error {
  constructor(kind, status = 0) {
    super(kind);
    this.kind = kind;
    this.status = status;
  }
}

export async function settings() {
  return { ...DEFAULTS, ...(await chrome.storage.local.get(Object.keys(DEFAULTS))) };
}

export async function remember(values) {
  await chrome.storage.local.set(values);
}

export async function api(path, init = {}) {
  const { server, token } = await settings();
  let response;
  try {
    response = await fetch(server.replace(/\/+$/, "") + path, {
      ...init, headers: { "X-Tarjim-Token": token, ...(init.headers || {}) },
    });
  } catch {
    throw new ApiError("offline");
  }
  if (response.status === 403) throw new ApiError("token", 403);
  if (!response.ok) {
    const error = new ApiError("http", response.status);
    error.body = await response.json().catch(() => ({}));
    throw error;
  }
  return response.json();
}

export const post = (path, body) => api(path, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}),
});

export const stageLabel = (stage) => t(STAGE_KEYS[stage] || "stageQueued");

export const errorLabel = (job) => t(ERROR_KEYS[job.error_code] || "errUnknown");

export function stepsFor(job) {
  const wanted = { downloading: job.link, burning: job.mode !== "srt", dubbing: job.mode.startsWith("dub") };
  return STAGES.filter((stage) => wanted[stage] ?? true);
}

export function mediaUrl(url) {
  return typeof url === "string" && /^https?:\/\//i.test(url) && !/^https?:\/\/(127\.0\.0\.1|localhost)/i.test(url);
}

export function modeLabel(mode) {
  if (mode.startsWith("dub")) return t("outputDub");
  return t(mode === "srt" ? "outputSrt" : "outputBurn");
}