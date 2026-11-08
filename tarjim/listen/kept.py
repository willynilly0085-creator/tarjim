"""The hearing kept beside a clip's other work, so a re-run does not pay to listen again, with the
stretches asked about again (listen/asked.py) and the transcript made from it. "Listen again"
forgets them all.

Since 2026-11-08 a hearing that left speech out is kept too: before, one stretch nothing could fill
made every later run pay to listen to the whole clip again, and a computer without the local
listener listened again forever. Now only the stretches left out are asked about again, each at
most TRIES times across runs (listen/repair.py). The transcript carries a key made from the code
(listen/derive.py) and the settings it was derived with; another key means it is derived again
from the kept hearing, with no new listening, so a fix reaches a clip done before it.

Since 2026-11-08 a long clip's hearing keeps each piece with its own passes, so it is voted again
piece by piece as it was heard (listen/chunks.joined); one kept before that is used as it was
voted. Each fill keeps the stretch it filled (listen/fills.py judges it again on every run).
"""
import functools
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from tarjim import guards
from tarjim.asr.base import Transcript
from tarjim.asr.sanity import implausible
from tarjim.listen.asked import ASKED, TRIES, Asked, Spent
from tarjim.listen.chunks import joined
from tarjim.listen.derive import with_imports
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import ONE_PASS, PASSES, Fill, Heard, Piece
from tarjim.models import Word

HEARD = "heard.json"
TRANSCRIPT = "transcript.json"
MADE_FROM_IT = "cues.*.json"
DERIVE = "derive"
ROOT = Path(__file__).resolve().parent.parent
# with every tarjim module these import at the top (listen/derive.py)
DERIVED_FROM = ("listen", "asr", "segment.py", "dialogue.py", "model_pins.py", "hearing.py")
# the settings that choose how a hearing is derived; each later mode setting joins them. Since
# 2026-11-09 the person's own listening settings too (tarjim/prefs), each named in the key only
# when it is not its default, so a transcript kept before them is still the one derived now.
MODES = ("aligner_mode", "listen.passes", "listen.second_opinion", "listen.voice_check")

Row = dict[str, Any]
# the record of stretches asked again lived here before 2026-11-08 (now listen/asked.py)
__all__ = ["ASKED", "TRIES", "Asked", "Spent"]


def lines_of(rows: list[Row] | None) -> list[Utterance]:
    return [Utterance(**row) for row in rows or []]


def fill_of(row: Row) -> Fill:
    """A kept fill; one kept before 2026-11-08 is a bare line, with no stretch."""
    if "line" not in row:
        return Fill(Utterance(**row))
    gap = row.get("gap")
    return Fill(Utterance(**row["line"]), None if gap is None else (float(gap[0]), float(gap[1])))


def piece_of(row: Row) -> Piece:
    return Piece(float(row["start"]), float(row["end"]), [lines_of(run) for run in row["passes"]])


def load_heard(cache: Path) -> Heard | None:
    kept = cache / HEARD
    if not kept.exists():
        return None
    data = json.loads(kept.read_text(encoding="utf-8"))
    pieces = [piece_of(row) for row in data.get("pieces") or []]
    guards.when("kept.revoted", bool(pieces))  # voted again piece by piece below
    voted, passes = joined(pieces) if pieces else (
        lines_of(data["utterances"]), [lines_of(run) for run in data.get("passes") or []])
    words, provider = data.get("local_words"), str(data.get("provider") or "")
    # kept before 2026-11-09 with no count: asked as many as every hearing was then
    asked = data.get("asked") or (1 if provider in ONE_PASS else PASSES)
    return Heard(data["language"], voted, passes,
                 None if words is None else [Word(**w) for w in words],
                 provider, [fill_of(row) for row in data.get("added") or []],
                 pieces, empty=int(data.get("empty") or 0), asked=int(asked))


def keep_heard(cache: Path, heard: Heard) -> None:
    (cache / HEARD).write_text(json.dumps(asdict(heard), ensure_ascii=False, indent=1),
                               encoding="utf-8")


def sources(path: Path) -> list[Path]:
    return sorted(path.rglob("*.py")) if path.is_dir() else [path]


def key_files() -> list[Path]:
    """The files named and every tarjim module they import at the top (2026-11-08)."""
    return with_imports([p for name in DERIVED_FROM for p in sources(ROOT / name)], ROOT)


@functools.cache
def code_key() -> str:
    """The code the transcript is derived with, the same on every system (line ends aside)."""
    digest = hashlib.sha256()
    for path in key_files():
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def derive_key() -> str:
    """The code and the listening settings that change what is derived from a hearing. Since
    2026-11-08 the mode settings are in it too: a clip timed in one aligner mode would otherwise
    be served as timed in the other (config is not followed into the code key, listen/derive)."""
    from tarjim.listen.chunks import chunk_seconds
    from tarjim.listen.coverage import gap_seconds

    modes = "".join(mode(name) for name in MODES)
    chosen = f"{code_key()}|chunk={chunk_seconds()}|gap={gap_seconds()}{modes}"
    return hashlib.sha256(chosen.encode()).hexdigest()[:16]


def mode(name: str) -> str:
    """One setting as the key holds it: a setup setting always, a person's one when changed."""
    from tarjim.config import setting
    from tarjim.prefs.active import active
    from tarjim.prefs.table import SPECS

    if name not in SPECS:
        return f"|{name}={setting(name)}"
    value = active().values[name]
    return "" if value == SPECS[name].default else f"|{name}={value}"


def keep_transcript(cache: Path, transcript: Transcript) -> None:
    data = {DERIVE: derive_key(), **asdict(transcript)}
    (cache / TRANSCRIPT).write_text(json.dumps(data, ensure_ascii=False, indent=1),
                                    encoding="utf-8")


def kept_transcript(cache: Path) -> tuple[Transcript, bool] | None:
    """The kept transcript, and whether it was derived by the code and settings running now."""
    try:
        data = json.loads((cache / TRANSCRIPT).read_text(encoding="utf-8"))
        current = data.pop(DERIVE, None) == derive_key()
        words = [Word(**w) for w in data.pop("words")]
        return Transcript(words=words, **data), current
    except (OSError, ValueError, KeyError, TypeError):
        return None


def reusable(cache: Path) -> Transcript | None:
    """The kept transcript, when the code and settings running now derived it and a person could
    speak its timing. Since 2026-11-08 another key means it is derived again from the kept
    hearing, on this computer: a timing kept by older code was replayed on every run."""
    found = kept_transcript(cache)
    if found is None or guards.when("kept.implausible", implausible(found[0].words)):
        return None  # a broken timing kept by an older run is made again
    if not found[1] and (cache / HEARD).exists():
        guards.fired("kept.rederived")
        print("timing: the kept transcript was made by other code or settings; it is made "
              "again from the kept hearing, with no new listening", flush=True)
        return None
    return found[0]


def rederiving(cache: Path) -> bool:
    """The kept transcript is derived again from the kept hearing: what that asks again is paid
    because the code or settings changed, and the log says so (2026-11-08)."""
    found = kept_transcript(cache)
    return found is not None and not found[1] and (cache / HEARD).exists()


def forget(cache: Path) -> None:
    """What a "listen again" clears: the hearing, what was asked again, its transcript and the
    lines made from them."""
    gone = [p for p in [cache / HEARD, cache / ASKED, cache / TRANSCRIPT,
                        *cache.glob(MADE_FROM_IT)] if p.exists()]
    for path in gone:
        path.unlink(missing_ok=True)
    print(f"listen again: cleared {len(gone)} kept file(s) for {cache.name}", flush=True)
