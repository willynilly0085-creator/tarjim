// Runs inside pages (no imports): shows the translation of the selected text in a small card
// under it. Put into a page by a right-click on a selection, or into every page once the
// person chose "as I select" in the settings and allowed it. The text goes to the extension's
// background, which asks the person's own tarjim; nothing is read until something is selected.
(() => {
  if (globalThis.tarjimSelection) return;
  globalThis.tarjimSelection = true;
  const MOST = 6000;  // the engine's limit (tarjim/text.py): a longer selection is told so
  const GAP = 8;
  const STYLE = `
    :host { all: initial; position: absolute; z-index: 2147483647; }
    .card { --bg: oklch(0.975 0.006 95); --raised: oklch(0.945 0.008 95); --line: oklch(0.87 0.009 95);
      --text: oklch(0.23 0.012 95); --muted: oklch(0.46 0.012 95); --focus: oklch(0.56 0.12 88);
      box-sizing: border-box; width: max-content; max-width: min(420px, calc(100vw - 16px));
      max-height: min(50vh, 420px); overflow: auto; padding: 12px 16px; border: 1px solid var(--line);
      border-radius: 10px; background: var(--bg); color: var(--text);
      font: 15px/1.6 system-ui, "Segoe UI", Tahoma, sans-serif; text-align: start;
      box-shadow: 0 6px 24px oklch(0.2 0.01 95 / 0.18); animation: in 160ms cubic-bezier(0.22, 1, 0.36, 1); }
    .card.ask { padding: 4px; }
    @media (prefers-color-scheme: dark) { .card { --bg: oklch(0.19 0.008 95); --raised: oklch(0.235 0.009 95);
      --line: oklch(0.32 0.01 95); --text: oklch(0.93 0.008 95); --muted: oklch(0.72 0.01 95);
      --focus: oklch(0.85 0.15 95); } }
    @keyframes in { from { opacity: 0; transform: translateY(4px); } }
    @media (prefers-reduced-motion: reduce) { .card { animation: none; } }
    p { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }
    p.quiet { color: var(--muted); }
    .row { display: flex; justify-content: flex-end; margin-top: 8px; }
    button { all: unset; box-sizing: border-box; padding: 4px 12px; border: 1px solid var(--line);
      border-radius: 8px; color: var(--muted); font: 550 13px/1.5 system-ui, "Segoe UI", Tahoma, sans-serif;
      cursor: pointer; }
    .ask button { border-color: transparent; color: var(--text); }
    button:hover { background: var(--raised); color: var(--text); }
    button:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px; }`;
  let host = null;
  let words = null;
  let mode = "menu";
  let asked = 0;
  let shownFor = "";
  let settle = 0;

  const PLAIN = { working: "…", copy: "Copy", copied: "Copied", ask: "tarjim", long: "", dir: "auto" };
  const send = (message) => chrome.runtime.sendMessage(message).catch(() => null);
  const worded = async () => { words ||= (await send({ type: "tarjim-words" })) || PLAIN; };
  const make = (tag, props = {}) => Object.assign(document.createElement(tag), props);

  function picked() {
    const selection = globalThis.getSelection();
    const text = selection ? selection.toString().trim() : "";
    const box = text && selection.rangeCount ? selection.getRangeAt(0).getBoundingClientRect() : null;
    return { text, box: box && (box.width || box.height) ? box : null };
  }

  function close() {
    host?.remove();
    host = null;
    shownFor = "";
    asked += 1;  // an answer still on its way belongs to a card that is gone
  }

  // Under the selection, or above it when there is no room below; never off the side.
  function place(box) {
    const card = host.getBoundingClientRect();
    const at = box || { left: (innerWidth - card.width) / 2, top: GAP, bottom: GAP };
    const below = at.bottom + GAP + card.height <= innerHeight || at.top - GAP - card.height < 0;
    const left = Math.max(GAP, Math.min(at.left, innerWidth - card.width - GAP));
    host.style.left = `${scrollX + left}px`;
    host.style.top = `${scrollY + (below ? at.bottom + GAP : at.top - GAP - card.height)}px`;
  }

  function show(box, kind, children) {
    host?.remove();
    host = make("div");
    const card = make("div", { className: `card ${kind}`, dir: words?.dir || "auto" });
    card.setAttribute("role", "status");
    card.append(...children);
    host.attachShadow({ mode: "closed" }).append(make("style", { textContent: STYLE }), card);
    document.documentElement.append(host);
    place(box);
  }

  function copyRow(text) {
    const button = make("button", { type: "button", textContent: words.copy });
    button.addEventListener("click", async () => {
      await navigator.clipboard.writeText(text).catch(() => null);
      button.textContent = words.copied;
    });
    const row = make("div", { className: "row" });
    row.append(button);
    return row;
  }

  async function translate(text, box) {
    await worded();
    const mine = ++asked;
    shownFor = text;
    if (text.length > MOST) return show(box, "", [make("p", { className: "quiet", textContent: words.long })]);
    show(box, "", [make("p", { className: "quiet", textContent: words.working })]);
    const reply = (await send({ type: "tarjim-text", text })) || {};
    if (mine !== asked) return;
    if (!reply.translation) return show(box, "", [make("p", { className: "quiet", textContent: reply.message || "" })]);
    show(box, "", [make("p", { dir: "auto", textContent: reply.translation }), copyRow(reply.translation)]);
  }

  async function offer(text, box) {
    await worded();
    shownFor = text;
    const button = make("button", { type: "button", textContent: words.ask });
    button.addEventListener("click", () => translate(text, box));
    show(box, "ask", [button]);
  }

  const typing = () => document.activeElement?.matches?.("input, textarea, [contenteditable]:not([contenteditable=false])");

  // "As I select": once the selection has settled, and never while the person is typing.
  function selected(event) {
    if (mode === "menu" || (host && event.composedPath().includes(host))) return;
    clearTimeout(settle);
    settle = setTimeout(() => {
      const { text, box } = picked();
      if (text.length < 2 || text === shownFor || typing()) return;
      (mode === "card" ? translate : offer)(text, box);
    }, 250);
  }

  chrome.runtime.onMessage.addListener((message) => {
    if (message?.type !== "tarjim-selection") return;
    const { text, box } = picked();
    if (message.text || text) translate(text || message.text.trim(), box);
  });
  document.addEventListener("mouseup", selected);
  document.addEventListener("keyup", (event) => { if (event.shiftKey || event.key === "Shift") selected(event); });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") close(); });
  document.addEventListener("mousedown", (event) => { if (host && !event.composedPath().includes(host)) close(); });
  chrome.storage.local.get({ textMode: "menu" }).then((saved) => { mode = saved.textMode; });
  chrome.storage.onChanged.addListener((changes) => { if (changes.textMode) mode = changes.textMode.newValue || "menu"; });
})();
