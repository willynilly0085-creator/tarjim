import { $, api, post } from "./api.js";
import { t } from "./i18n.js";

const DONE_MS = 5000;
let pending = [];

async function check() {
  if ($("pair-form").hidden) return;
  pending = await api("/pairs").catch(() => []);
  $("pairing").hidden = !pending.length;
}

function showDone() {
  $("pair-ask").textContent = t("paired");
  $("pair-form").hidden = true;
  setTimeout(() => {
    $("pairing").hidden = true;
    $("pair-ask").textContent = t("pairAsk");
    $("pair-form").hidden = false;
  }, DONE_MS);
}

// Allow answers the request waiting longest; no code is asked (the owner's choice).
async function allow(event) {
  event.preventDefault();
  const first = pending[0];
  if (first && await post(`/pairs/${first.id}/allow`).then(() => true, () => false)) showDone();
}

async function denyAll() {
  await Promise.all(pending.map((r) => post(`/pairs/${r.id}/deny`).catch(() => null)));
  pending = [];
  $("pairing").hidden = true;
}

export function watchPairing() {
  $("pair-form").addEventListener("submit", allow);
  $("pair-deny").addEventListener("click", denyAll);
  check();
  setInterval(check, 3000);
}
