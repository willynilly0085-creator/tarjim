import { post } from "./api.js";
import { t } from "./i18n.js";

const WATCH_MS = 3000;
const WATCH_LIMIT = 100;
let watching = 0;

function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children.filter((child) => child !== ""));
  return node;
}

async function isSignedIn(provider) {
  const { signed_in: yes } = await post("/connections/signed-in", { provider }).catch(() => ({}));
  return Boolean(yes);
}

function codeForm(provider, note) {
  const input = el("input", { className: "text-input", dir: "ltr", autocomplete: "off", spellcheck: false });
  const form = el("form", { className: "row", noValidate: true },
    el("label", { className: "field grow" }, el("span", { className: "field-label", textContent: t("signInCodeLabel") }), input),
    el("button", { type: "submit", className: "button-quiet", textContent: t("signInCodeSend") }));
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    await post("/connections/sign-in/code", { provider, code: input.value.trim() }).catch(() => null);
    input.value = "";
    note.textContent = t("signInWaiting");
  });
  return form;
}

function watch(provider, note, done) {
  clearInterval(watching);
  let rounds = 0;
  watching = setInterval(async () => {
    rounds += 1;
    if (rounds > WATCH_LIMIT || !note.isConnected) clearInterval(watching);
    else if (await isSignedIn(provider)) {
      clearInterval(watching);
      done();
    }
  }, WATCH_MS);
}

export function signInPanel(provider) {
  const note = el("p", { className: "meta", role: "status", textContent: t("subscriptionReady") });
  const button = el("button", { type: "button", className: "button-quiet", textContent: t("signIn") });
  const box = el("div", { className: "sign-in" }, note, button);
  const signedIn = () => box.replaceChildren(el("p", { className: "meta ok", role: "status", textContent: t("signedIn") }));
  isSignedIn(provider.id).then((yes) => { if (yes) signedIn(); });
  button.addEventListener("click", async () => {
    const { mode } = await post("/connections/sign-in", { provider: provider.id }).catch(() => ({}));
    if (!mode) {
      note.textContent = t("signInFailed");
      return;
    }
    note.textContent = t(mode === "browser" ? "signInWaiting" : "signInConsole");
    if (mode === "browser") box.replaceChildren(note, codeForm(provider.id, note));
    watch(provider.id, note, signedIn);
  });
  return box;
}
