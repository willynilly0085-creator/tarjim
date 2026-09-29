export const $ = (id) => document.getElementById(id);

export function show(view) {
  document.querySelectorAll(".view").forEach((el) => { el.hidden = el.id !== `view-${view}`; });
}
