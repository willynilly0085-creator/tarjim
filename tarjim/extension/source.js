// What the popup translates: the video on this tab, a link the right-click menu handed over, or
// (on the full page) a file or a pasted link. A link's qualities are read as soon as it is known.
import { $ } from "./dom.js";
import { downloadable } from "./posts.js";
import { askQuality, heardLink, qualityTitle } from "./quality.js";

const FRESH = 10 * 60 * 1000;

// The right-click menu opens this window with its link instead of starting at once, so the
// quality is picked here (the owner, 2026-10-24). The link waits ten minutes, as long as a
// pairing request may wait for its Allow on the computer, so a first right-click is not lost.
async function pending() {
  const { pendingLink } = await chrome.storage.local.get("pendingLink");
  return pendingLink?.url && Date.now() - pendingLink.at < FRESH ? pendingLink.url : "";
}

export const clearPending = () => chrome.storage.local.remove("pendingLink");

function onPage(link) {
  $("source-tab").hidden = true;
  $("drop").hidden = false;
  $("open-file-page").hidden = true;
  if (!link) return;
  $("link").value = link;
  heardLink(link);
}

// The link to translate when this is the popup; on the full page the link is read from its field.
export async function describeSource(pageMode) {
  const link = await pending();
  if (pageMode) return onPage(link) ?? "";
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = link || (downloadable(tab?.url) ? tab.url : "");
  const own = url === tab?.url;
  $("source-tab").hidden = !url;
  $("source-none").hidden = Boolean(url);
  $("tab-title").textContent = own ? tab?.title || "" : url;
  $("tab-host").textContent = url ? new URL(url).hostname.replace(/^www\./, "") : "";
  if (url) askQuality(url, false).then(() => { if (!own && qualityTitle()) $("tab-title").textContent = qualityTitle(); });
  return url;
}
