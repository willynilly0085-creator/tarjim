"""The clip's speech map (asr/speechmap.py), made once per job and kept beside the hearing as
speech.json (2026-11-09).

The voice detector ran about twice a job before: once for the coverage check and again inside
every alignment, on the clip and on each stretch of it. Now it runs once per sound file
(`regions_of`, shared with the long clip's cutting in hearing.py), and every timing reads the one
map. speech.json carries the key the transcript is derived with (listen/kept.derive_key): a map
kept by other code or settings is made again; "listen again" clears it. Every hearing leaves one,
those that time nothing too (`untimed_map`), so what reads it later always finds the clip's.
"""
import json
from pathlib import Path
from typing import Any, NamedTuple

from tarjim.asr.ctc import FRAME
from tarjim.asr.speechmap import SpeechMap, build, restored
from tarjim.listen.kept import DERIVE, SPEECH, derive_key

Regions = list[tuple[float, float]]
Stat = tuple[str, int, int]

DETECTED: dict[Stat, Regions] = {}  # the last sound file's speech, by its path, size and time


class Clip(NamedTuple):
    audio: Path  # the sound file the samples were read from
    wav: Any
    rate: int


def regions_of(audio: Path, wav: Any = None) -> Regions:
    """The voice detector's speech in the sound file, run once for it (listen/check.regions_in);
    `wav`, when given, is the file's samples already read."""
    from tarjim.listen import check

    stat = audio.stat()
    key = (str(audio.resolve()), stat.st_size, stat.st_mtime_ns)
    if key not in DETECTED:
        if wav is None:
            import soundfile

            wav, _ = soundfile.read(str(audio), dtype="float32")
        DETECTED.clear()  # one file's at a time: a few spans
        DETECTED[key] = check.regions_in(wav)
    return DETECTED[key]


def letters_of(wav: Any) -> Any:
    """The whole clip's letters, as the aligner hears them once (asr/letters.Letters); None for a
    stand-in aligner with no ears."""
    from tarjim.asr.align import shared_aligner
    from tarjim.memory import heavy

    with heavy():
        emitter = getattr(shared_aligner(), "emitter", None)
        return None if emitter is None else emitter.emissions(wav)


def kept_map(cache: Path, frames: int | None) -> SpeechMap | None:
    """The map kept for this clip, when the code and settings running now made it (and it is
    `frames` long, when that is given)."""
    try:
        data = json.loads((cache / SPEECH).read_text(encoding="utf-8"))
        if data.get(DERIVE) != derive_key() or frames not in (None, int(data["frames"])):
            return None
        return restored(data)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def keep_map(cache: Path, made: SpeechMap) -> None:
    data = {DERIVE: derive_key(), **made.summary()}
    try:
        (cache / SPEECH).write_text(json.dumps(data), encoding="utf-8")
    except OSError as error:  # the map is made again next time; nothing else depends on it
        print(f"speech: the speech map was not kept ({type(error).__name__})", flush=True)


def clip_map(cache: Path, clip: Clip, heard: Regions) -> SpeechMap:
    """The clip's map with the heard lines over silence made soft; kept, or made and kept."""
    letters = letters_of(clip.wav)
    frames = len(letters) if letters is not None else int(len(clip.wav) / clip.rate / FRAME)
    made = kept_map(cache, frames)
    if made is None:
        made = build(letters, frames, regions_of(clip.audio, clip.wav))
        keep_map(cache, made)
    print(f"speech: {sum(b - a for a, b in made.speech()):.1f} s of speech ({made.source}, "
          f"{sum(b - a for a, b in made.ctc_only()):.1f} s heard by the letters alone)", flush=True)
    return made.heard(heard)


def untimed_map(cache: Path, audio: Path) -> SpeechMap | None:
    """The map of a hearing that times nothing (the local listener standing in, or no speech
    heard, 2026-11-09): the one kept for this code, else the detector's alone, its letters not
    heard (source "none": a check reading it says it could not check). No letters are heard for
    it: on these paths the aligner never ran, and a weak computer is not made to run it. None
    when the sound cannot be read: the transcript stands without it."""
    import soundfile

    made = kept_map(cache, None)
    if made is not None:
        return made
    try:
        made = build(None, int(soundfile.info(str(audio)).duration / FRAME), regions_of(audio))
    except (OSError, RuntimeError) as error:  # soundfile's own errors are RuntimeErrors
        print(f"speech: no speech map ({type(error).__name__})", flush=True)
        return None
    keep_map(cache, made)
    return made
