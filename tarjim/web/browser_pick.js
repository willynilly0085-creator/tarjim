// "إضافة المتصفح" (2026-11-25): Chrome and Firefox as two equal choices, each with its own steps,
// where Firefox used to sit folded under Chrome's. It starts on the browser this page is open in;
// in Firefox the signed add-on is one press, elsewhere its link is copied to open in Firefox.
import { $ } from "./api.js";

let picked = "";
let wired = false;

const inFirefox = () => navigator.userAgent.includes("Firefox/");

function show(browser) {
  picked = browser;
  $("steps-chrome").hidden = browser !== "chrome";
  $("steps-firefox").hidden = browser !== "firefox";
  const radio = document.querySelector(`input[name=browser][value=${browser}]`);
  if (radio) radio.checked = true;
}

// link: the newest release's signed add-on (setup's firefox_link).
export function fillBrowserSteps(link) {
  const here = inFirefox();
  $("firefox-install").href = link;
  document.querySelectorAll("#steps-firefox .in-firefox").forEach((step) => { step.hidden = !here; });
  document.querySelectorAll("#steps-firefox .not-firefox").forEach((step) => { step.hidden = here; });
  if (!wired) {
    document.querySelectorAll("input[name=browser]").forEach((radio) => {
      radio.addEventListener("change", () => show(radio.value));
    });
    wired = true;
  }
  show(picked || (here ? "firefox" : "chrome"));
}
