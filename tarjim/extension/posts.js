// Which post a right-clicked video belongs to. Sites like X play videos from a temporary blob:
// address, and the page itself may be a feed, so neither can be downloaded. The clicked video is
// found by that blob address and the nearest link to its post is used instead.

const POST = /\/status\/\d+|\/watch\?v=|youtu\.be\/|\/shorts\/|\/reels?\/|\/p\/[\w-]+|\/video\/\d+|\/videos\/\d+/;
const FEEDS = /^https?:\/\/([\w-]+\.)?(x|twitter|youtube|instagram|tiktok|facebook)\.com\//i;

export function isPost(url) {
  return POST.test(url || "");
}

export function downloadable(url) {
  if (!/^https?:\/\//i.test(url || "") || /^https?:\/\/(127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.|\[|localhost|[^/]*\.(local|lan|internal)([:/]|$))/i.test(url)) return false;
  return !FEEDS.test(url) || isPost(url);
}

// Runs inside the page (chrome.scripting), so it must not use anything from outside itself.
export function postOfVideo(src) {
  const post = /\/status\/\d+|\/watch\?v=|youtu\.be\/|\/shorts\/|\/reels?\/|\/p\/[\w-]+|\/video\/\d+|\/videos\/\d+/;
  const video = [...document.querySelectorAll("video")].find((v) => v.currentSrc === src || v.src === src);
  for (let node = video; node && node !== document.documentElement; node = node.parentElement) {
    const link = [...node.querySelectorAll("a[href]")].find((a) => post.test(a.href));
    if (link) return link.href;
  }
  return post.test(location.href) ? location.href : "";
}

export async function clickedPost(info, tab) {
  if (!tab?.id || !info.srcUrl?.startsWith("blob:")) return "";
  try {
    const [found] = await chrome.scripting.executeScript({
      target: { tabId: tab.id, frameIds: [info.frameId ?? 0] }, func: postOfVideo, args: [info.srcUrl] });
    return found?.result || "";
  } catch {
    return "";
  }
}
