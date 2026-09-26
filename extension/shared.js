export const DEFAULTS = { server: "http://127.0.0.1:17653", token: "", target: "ar", dialect: "saudi", mode: "burn", voice: "clone" };

export const STAGES = ["downloading", "hearing", "translating", "writing", "burning", "dubbing"];
const STAGE_KEYS = {
  queued: "stageQueued", downloading: "stageDownloading", hearing: "stageHearing",
  translating: "stageTranslating", writing: "stageWriting", burning: "stageBurning", dubbing: "stageDubbing",
  done: "stageDone", failed: "stageFailed",
};
const ERROR_KEYS = { quota: "errQuota", key: "errKey", download: "errDownload", tools: "errTools", dub: "errDub" };

export const t = (key, ...subs) => chrome.i18n.getMessage(key, subs) || key;

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
  if (!response.ok) throw new ApiError("http", response.status);
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