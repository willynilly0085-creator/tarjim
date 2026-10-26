import { $ } from "./dom.js";
import { ApiError, settings, t } from "./shared.js";

const MEDIA = /\.(mp4|mkv|webm|mov|avi|m4v|mp3|m4a|wav|flac|ogg|opus|aac)$/i;
const LARGEST = 8 * 1024 ** 3;  // the most tarjim takes in one upload (MAX_UPLOAD)
// Why tarjim did not take a translation, by the reason it gave.
const REFUSED = { "bad url": "sendBadLink", file: "sendFile" };

export const isMedia = (file) => Boolean(file) && MEDIA.test(file.name);
export const tooBig = (file) => file.size > LARGEST;
export const sendProblem = (error) => t(REFUSED[error.body?.error] || "sendFailed");

export function showProgress(fraction) {
  $("upload").hidden = false;
  $("upload-bar").style.transform = `scaleX(${fraction})`;
  $("upload-text").textContent = `${t("uploading")} ${Math.round(fraction * 100)}%`;
}

function refused(request) {
  const error = new ApiError("http", request.status);
  try {
    error.body = JSON.parse(request.responseText);
  } catch {
    error.body = {};
  }
  return error;
}

export async function upload(file, fields, onProgress) {
  const { server, token } = await settings();
  const query = new URLSearchParams({ name: file.name, ...fields });
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `${server.replace(/\/+$/, "")}/upload?${query}`);
    request.setRequestHeader("X-Tarjim-Token", token);
    request.upload.onprogress = (event) => event.lengthComputable && onProgress(event.loaded / event.total);
    request.onload = () => {
      if (request.status === 403) return reject(new ApiError("token", 403));
      if (request.status !== 200) return reject(refused(request));
      resolve(JSON.parse(request.responseText));
    };
    request.onerror = () => reject(new ApiError("offline"));
    request.send(file);
  });
}
