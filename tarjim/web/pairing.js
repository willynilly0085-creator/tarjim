import { $, api, post } from "./api.js";
import { t } from "./i18n.js";

const DONE_MS = 5000;
let pending = [];

// Digits typed on an Arabic or Persian keyboard count the same as 0-9.
const digits = (text) => text.trim().replace(/[٠-٩۰-۹]/g, (d) => String(d.charCodeAt(0) & 0xf));

async function check() {
  if ($("pair-form").hidden) return;
  pending = await api("/pairs").catch(() => []);
  $("pairing").hidden = !pending.length;
}

function showDone() {
  $("pair-code").value = "";
  $("pair-ask").textContent = t("paired");
  $("pair-form").hidden = true;
  setTimeout(() => {
    $("pairing").hidden = true;
    $("pair-ask").textContent = t("pairAsk");
    $("pair-form").hidden = false;
  }, DONE_MS);
}

// Only the request showing the code the person typed is allowed, and the engine checks the code too.
async function allow(event) {
  event.preventDefault();
  const code = digits($("pair-code").value);
  const match = pending.find((r) => r.code === code);
  const done = match ? await post(`/pairs/${match.id}/allow`, { code }).then(() => true, () => false) : false;
  $("pair-error").hidden = done;
  if (done) return showDone();
  $("pair-code").select();
}

async function denyAll() {
  await Promise.all(pending.map((r) => post(`/pairs/${r.id}/deny`).catch(() => null)));
  pending = [];
  $("pair-code").value = "";
  $("pair-error").hidden = true;
  $("pairing").hidden = true;
}

export function watchPairing() {
  $("pair-form").addEventListener("submit", allow);
  $("pair-deny").addEventListener("click", denyAll);
  $("pair-code").addEventListener("input", () => { $("pair-error").hidden = true; });
  check();
  setInterval(check, 3000);
}
