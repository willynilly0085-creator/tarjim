"""The cloud listener faked at its boundary, so tarjim's own re-listening runs in full.

`media.audio_bytes` returns a token naming the stretch instead of sound, and
`hearing.cloud_listener` returns a fake that reads the token back and answers what the Oracle
hears there, at the stretch's own times, through tarjim's real `merge.listen_many` (each pass one
oracle call). So `check.relistener`, `chunks.shift`, `asked.Asked` and any budget above them are
tarjim's real code. A fresh whole-clip hearing (`hearing.listen_video`, reached only when the
kept hearing heard nothing) goes through the real `listen_with` and the same fake.

Oracle modes:
    good    the truth words inside the stretch, one line per truth sentence, named S1, S2, ...
            by first appearance in the request, as a cloud listener names them
    none    nothing
    invent  good, plus 20% more lines invented on the stretch's silences (alike in every pass)
    quota   good for the first `quota_after` passes, then tarjim.gemini_client.QuotaExhausted
"""
import random
import threading
from collections.abc import Callable
from dataclasses import replace
from typing import Any

import score
from tarjim.gemini_client import QuotaExhausted
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import PASSES, Heard, listen_many

TOKEN = "tarjim-bench-span:"
INVENT_SHARE = 0.2
SILENCE = 1.0  # seconds without truth words: room for an invented line
INVENTED_LONG = 2.0
INVENTED = ("Thank you for watching.", "Please subscribe to the channel.",
            "Music playing in the background.", "See you in the next video.")
QUOTA_AFTER = 3

Truth = dict[str, Any]


def span_token(_video: Any, start: float = 0.0, end: float | None = None) -> bytes:
    return f"{TOKEN}{start!r}:{end!r}".encode()


def decoded(sound: bytes) -> tuple[float, float | None]:
    text = sound.decode()
    if not text.startswith(TOKEN):
        raise RuntimeError("bench: the fake cloud was given real sound")
    start, end = text[len(TOKEN):].split(":")
    return float(start), None if end == "None" else float(end)


class Oracle:
    """What a cloud listener hears in a stretch of the clip, by mode; every pass is a call."""

    def __init__(self, truth: Truth, mode: str = "good", seed: int = 0,
                 quota_after: int = QUOTA_AFTER) -> None:
        from measures import foreground

        self.all_words = truth["words"]
        self.truth = foreground(truth)
        self.mode, self.seed, self.quota_after = mode, seed, quota_after
        self.home = score.sentence_of(self.truth) if self.truth["sentences"] else []
        self.calls: list[list[float]] = []  # one per pass
        self.requests: list[list[float]] = []  # one per request (its passes together)
        self.refused = 0
        self.lock = threading.Lock()

    def counts(self) -> dict[str, Any]:
        return {"oracle_calls": len(self.calls), "oracle_requests": len(self.requests),
                "oracle_audio_s": round(sum(b - a for a, b in self.requests), 1),
                "oracle_refused": self.refused}

    def __call__(self, start: float, end: float) -> list[Utterance]:
        """One pass over the stretch, in clip times."""
        with self.lock:
            self.calls.append([round(start, 2), round(end, 2)])
            if self.mode == "quota" and len(self.calls) > self.quota_after:
                self.refused += 1
                raise QuotaExhausted("bench: free quota used up")
        if self.mode == "none":
            return []
        lines = self.heard(start, end)
        return sorted(lines + self.invented(start, end, len(lines)), key=lambda u: u.start) \
            if self.mode == "invent" else lines

    def heard(self, start: float, end: float) -> list[Utterance]:
        groups: dict[int, list[dict[str, Any]]] = {}
        for index, word in enumerate(self.truth["words"]):
            if start <= (word["start"] + word["end"]) / 2 <= end:
                groups.setdefault(self.home[index], []).append(word)
        names: dict[str, str] = {}
        lines = []
        for _, words in sorted(groups.items(), key=lambda g: g[1][0]["start"]):
            label = names.setdefault(words[0]["speaker"], f"S{len(names) + 1}")
            lines.append(Utterance(words[0]["start"], words[-1]["end"], label,
                                   " ".join(w["text"] for w in words)))
        return lines

    def silences(self, start: float, end: float) -> list[tuple[float, float]]:
        out, reach = [], start
        for w in sorted(self.all_words, key=lambda w: w["start"]):
            if w["end"] < start or w["start"] > end:
                continue
            if w["start"] - reach >= SILENCE:
                out.append((reach, w["start"]))
            reach = max(reach, w["end"])
        if end - reach >= SILENCE:
            out.append((reach, end))
        return out

    def invented(self, start: float, end: float, heard: int) -> list[Utterance]:
        """Seeded by the stretch, so every pass and every rerun invents the same."""
        rng = random.Random(f"{self.seed}:{start:.2f}:{end:.2f}")
        room = self.silences(start, end)
        want = max(1, round(INVENT_SHARE * heard)) if room else 0
        out = []
        for low, high in rng.sample(room, min(want, len(room))):
            a = low + 0.2
            out.append(Utterance(round(a, 3), round(min(high - 0.2, a + INVENTED_LONG), 3), "S1",
                                 rng.choice(INVENTED)))
        return out


def fake_cloud(oracle: Oracle, language: str, duration: float) -> Callable[..., Any]:
    """In place of hearing.cloud_listener(provider): any later arguments are taken, a `passes`
    keyword is honoured."""
    def cloud_listener(_provider: str, *_args: Any, **kwargs: Any) -> Callable[[bytes], Heard]:
        passes = int(kwargs.get("passes") or PASSES)

        def once(sound: bytes) -> Heard:
            start, end = decoded(sound)
            stop = duration if end is None else min(end, duration)
            with oracle.lock:
                oracle.requests.append([round(start, 2), round(stop, 2)])

            def listen() -> tuple[str, list[Utterance]]:
                lines = oracle(start, stop)
                return language, [replace(u, start=max(0.0, u.start - start),
                                          end=max(0.0, u.end - start)) for u in lines]

            return listen_many(listen, passes)

        return once

    return cloud_listener


def fresh_hearing(video: Any, audio: Any) -> Heard:
    """hearing.listen_video for the bench: the chosen cloud engine, faked, never a backup."""
    from tarjim import hearing

    return replace(hearing.listen_with("gemini", video, audio), provider="gemini", backup=False)
