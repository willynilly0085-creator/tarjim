// Saving on its own (2026-11-09): every change waits 400 ms for the next one, then all of them
// go in one request; a change made while a request is out waits for its answer and goes next,
// so two answers never race and the last value the person chose is the one kept.
export const WAIT = 400;

export function autosaver({ send, done, failed, wait = WAIT }) {
  let pending = {};
  let timer = 0;
  let flight = null;

  async function flush() {
    clearTimeout(timer);
    timer = 0;
    if (flight || !Object.keys(pending).length) return flight;
    const values = pending;
    pending = {};
    flight = (async () => {
      try {
        done(await send(values), values);
      } catch (error) {
        failed(error, values);
      }
    })();
    await flight;
    flight = null;
    if (Object.keys(pending).length) return flush();
    return null;
  }

  return {
    put(key, value) {
      pending[key] = value;
      clearTimeout(timer);
      timer = setTimeout(flush, wait);
    },
    waiting: (key) => key in pending,
    busy: () => Boolean(timer || flight),
    flush,
  };
}

// The status line's words for one answer from POST /prefs.
export function savedWords(answer, t) {
  const refused = Object.keys(answer.refused || {}).length;
  const said = refused ? t("prefsRefusedSome", { n: refused }) : t("prefsSaved");
  return [said, ...(answer.notes || [])].join(" ");
}

export function failedWords(error, t) {
  if (error?.offline) return t("prefsOffline");
  return t(error?.status === 503 ? "prefsBusy" : "prefsFailed");
}
