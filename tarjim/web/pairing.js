import { $, api, post } from "./api.js";
import { t } from "./i18n.js";

let current = null;

async function check() {
  const pending = await api("/pairs").catch(() => []);
  current = pending[0]?.id ?? null;
  $("pairing").hidden = !current;
}

async function decide(verdict) {
  if (!current) return;
  await post(`/pairs/${current}/${verdict}`);
  $("pairing").hidden = true;
  if (verdict === "allow") document.getElementById("announcer").textContent = t("paired");
  current = null;
}

export function watchPairing() {
  $("pair-allow").addEventListener("click", () => decide("allow"));
  $("pair-deny").addEventListener("click", () => decide("deny"));
  check();
  setInterval(check, 3000);
}
