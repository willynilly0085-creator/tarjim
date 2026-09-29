import { ApiError, settings } from "./shared.js";

const MEDIA = /\.(mp4|mkv|webm|mov|avi|m4v|mp3|m4a|wav|flac|ogg|opus|aac)$/i;

export const isMedia = (file) => Boolean(file) && MEDIA.test(file.name);

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
      if (request.status !== 200) return reject(new ApiError("http", request.status));
      resolve(JSON.parse(request.responseText));
    };
    request.onerror = () => reject(new ApiError("offline"));
    request.send(file);
  });
}
