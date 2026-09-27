export const $ = (id) => document.getElementById(id);

export async function api(path, init = {}) {
  const response = await fetch(path, { credentials: "same-origin", ...init });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(body.error || "http");
    error.status = response.status;
    error.body = body;
    throw error;
  }
  return body;
}

export const post = (path, data) => api(path, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data ?? {}),
});

export function upload(file, fields, onProgress) {
  const query = new URLSearchParams({ name: file.name, ...fields });
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `/upload?${query}`);
    request.upload.onprogress = (event) => event.lengthComputable && onProgress(event.loaded / event.total);
    request.onload = () => (request.status === 200 ? resolve(JSON.parse(request.responseText))
      : reject(new Error(String(request.status))));
    request.onerror = () => reject(new Error("offline"));
    request.send(file);
  });
}
