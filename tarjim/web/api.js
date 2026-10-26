export const $ = (id) => document.getElementById(id);

// A request that never reached the engine is told apart from one the engine refused.
const unreachable = () => Object.assign(new Error("offline"), { offline: true });

function refused(status, body) {
  return Object.assign(new Error(body.error || "http"), { status, body });
}

export async function api(path, init = {}) {
  const response = await fetch(path, { credentials: "same-origin", ...init }).catch(() => {
    throw unreachable();
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw refused(response.status, body);
  return body;
}

export const post = (path, data) => api(path, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data ?? {}),
});

function answer(request) {
  try {
    return JSON.parse(request.responseText);
  } catch {
    return {};
  }
}

export function upload(file, fields, onProgress) {
  const query = new URLSearchParams({ name: file.name, ...fields });
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `/upload?${query}`);
    request.upload.onprogress = (event) => event.lengthComputable && onProgress(event.loaded / event.total);
    request.onload = () => (request.status === 200 ? resolve(answer(request))
      : reject(refused(request.status, answer(request))));
    request.onerror = () => reject(unreachable());
    request.send(file);
  });
}
