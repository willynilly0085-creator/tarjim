// The words for a request that failed: the engine's own reason when the page knows it, then an
// engine that cannot be reached, then a page left open from an older start, then a plain retry.
import { t } from "./i18n.js";

export function problem(error, known = {}, values = {}) {
  const reason = known[error?.body?.error];
  if (reason) return t(reason, values);
  if (error?.offline) return t("sendOffline");
  return t(error?.status === 403 ? "pageExpired" : "actionFailed");
}
