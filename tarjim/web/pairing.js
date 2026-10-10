import { $, api, post } from "./api.js";
import { t } from "./i18n.js";

let current = null;

async function check() {
  if ($("pairing").querySelector(".row").hidden) return;
  const pending = await api("/pairs").catch(() => []);
  current = pending[0]?.id ?? null;
  $("pairing").hidden = !current;
  if (current) $("pairing").querySelector("p").textContent = `${t("pairAsk")} (${pending[0].code})`;
}

async function decide(verdict) {
  if (!current) return;
  await post(`/pairs/${current}/${verdict}`);
  current = null;
  if (verdict !== "allow") {
    $("pairing").hidden = true;
    return;
  }
  $("pairing").querySelector("p").textContent = t("paired");
  $("pairing").querySelector(".row").hidden = true;
  setTimeout(() => {
    $("pairing").hidden = true;
    $("pairing").querySelector("p").textContent = t("pairAsk");
    $("pairing").querySelector(".row").hidden = false;
  }, 5000);
}

export function watchPairing() {
  $("pair-allow").addEventListener("click", () => decide("allow"));
  $("pair-deny").addEventListener("click", () => decide("deny"));
  check();
  setInterval(check, 3000);
}
