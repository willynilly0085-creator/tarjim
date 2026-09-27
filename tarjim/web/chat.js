import { $, post } from "./api.js";
import { t } from "./i18n.js";

const APPS = ["claude-desktop", "claude-code", "codex"];

function row(app) {
  const item = $("tool-row").content.firstElementChild.cloneNode(true);
  item.querySelector(".tool-name").textContent = t(`chat_${app}`);
  item.querySelector(".tool-hint").textContent = t(`chat_${app}_hint`);
  const button = Object.assign(document.createElement("button"), { type: "button", className: "button-quiet", textContent: t("chatAdd") });
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await post("/connections/assistant", { app });
      item.querySelector(".tool-action").replaceChildren(Object.assign(document.createElement("span"), { className: "ready", textContent: t("chatAdded") }));
      item.querySelector(".tool-hint").textContent = t(app === "claude-desktop" ? "chatRestart" : `chat_${app}_hint`);
    } catch {
      button.disabled = false;
      item.querySelector(".tool-hint").textContent = t("chatFailed");
    }
  });
  item.querySelector(".tool-action").replaceChildren(button);
  return item;
}

export function renderChat() {
  $("chat-apps").replaceChildren(...APPS.map(row));
}
