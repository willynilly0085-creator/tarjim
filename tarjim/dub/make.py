import re
from pathlib import Path
from typing import Protocol

import numpy as np

from tarjim.config import setting
from tarjim.dub.audio import cut, write_wav
from tarjim.dub.clone import LANGUAGES as CLONE_LANGUAGES
from tarjim.dub.lines import Line, lines_from
from tarjim.dub.mix import mix, mux
from tarjim.dub.separate import Stems, separate
from tarjim.dub.studio import VOICES
from tarjim.dub.voices import reference_spans
from tarjim.job import Job, checkpoint
from tarjim.media import probe
from tarjim.memory import free_for_voice
from tarjim.models import Cue, Word

SAVED_VOICE = "fish:saved"
FIRST_SECONDS = 10.0
SAFE = re.compile(r"[^\w.-]")
NUMBER = re.compile(r"\d+")
PLAIN_TEXT = ("gemini", "clone")
KEYS = {"gemini": "gemini_api_key", "fish": "fish_api_key"}


class DubUnavailable(RuntimeError):
    pass


class Voices(Protocol):
    def speak_all(self, lines: list[Line]) -> list[np.ndarray]: ...


def choose(engine: str, language: str) -> str:
    """The voice asked for, or the one on this computer when it cannot be used. A voice on the
    computer is never swapped for a cloud one: the text would go to a company the person did not
    choose."""
    wanted = engine.split(":", maxsplit=1)[0]
    keyless = wanted in KEYS and not setting(KEYS[wanted])
    if keyless or (wanted == "studio" and language not in VOICES):
        wanted = "clone"
    if wanted == "clone" and language not in CLONE_LANGUAGES:
        raise DubUnavailable(f"no dubbing voice for language {language}")
    return wanted


def clone_installed() -> bool:
    from tarjim.tools import BY_ID, installed

    return installed(BY_ID["dubbing"])


def references(stems: Stems, words: list[Word], folder: Path) -> dict[str, Path]:
    folder.mkdir(parents=True, exist_ok=True)
    spans = {k: v for k, v in reference_spans(words).items() if v} or {"": [(0.0, FIRST_SECONDS)]}
    return {speaker: write_wav(folder / f"{SAFE.sub('_', speaker) or 'voice'}.wav",
                               cut(stems.voices, chosen))
            for speaker, chosen in spans.items()}


def voices_for(engine: str, spec: str, job: Job, samples: dict[str, Path]) -> Voices:
    if engine == "gemini":
        from tarjim.dub.gemini_voice import GeminiVoices

        return GeminiVoices(samples, job.target, job.dialect)
    if engine == "studio":
        from tarjim.dub.studio import StudioVoices

        return StudioVoices(sorted(samples), job.target)
    if engine == "fish":
        from tarjim.dub.fish import FishVoices

        saved = setting("fish_voice") if spec == SAVED_VOICE else ""
        return FishVoices(setting("fish_api_key"), samples, saved)
    from tarjim.dub.clone import CloneVoices

    return CloneVoices(samples, job.target)


def spell_numbers(text: str, language: str) -> str:
    from num2words import num2words

    def spell(match: re.Match[str]) -> str:
        try:
            return str(num2words(int(match.group()), lang=language))
        except (NotImplementedError, OverflowError, ValueError):
            return match.group()

    return NUMBER.sub(spell, text)


def spoken(lines: list[Line], engine: str, job: Job) -> list[Line]:
    from tarjim.dub.script import spoken_lines

    vowels = engine not in PLAIN_TEXT
    written = spoken_lines(lines, job.language.name, job.dialect, full_vowels=vowels)
    if written is not None:
        return written
    return fallback_spoken(lines, engine, job.target)


def fallback_spoken(lines: list[Line], engine: str, language: str) -> list[Line]:
    if engine in ("studio", "gemini"):
        return lines
    texts = [spell_numbers(line.text, language) for line in lines]
    if language == "ar" and engine not in PLAIN_TEXT:
        from tarjim.dub.tashkeel import add_vowels

        texts = add_vowels(texts)
    return [Line(line.start, line.until, line.speaker, text, line.source)
            for line, text in zip(lines, texts, strict=True)]


def speak(engine: str, job: Job, samples: dict[str, Path], lines: list[Line]) -> list[np.ndarray]:
    """A natural voice that fails is replaced by the voice on this computer, when there is one;
    otherwise the person sees why the natural voice failed."""
    try:
        return voices_for(engine, job.dub, job, samples).speak_all(lines)
    except RuntimeError:
        if engine != "gemini" or job.target not in CLONE_LANGUAGES or not clone_installed():
            raise
    backup = "clone"
    return voices_for(backup, backup, job, samples).speak_all(
        fallback_spoken(lines, backup, job.target))


def dub_video(job: Job, cues: list[Cue], words: list[Word], picture: Path) -> Path:
    engine = choose(job.dub, job.target)
    lines = spoken(lines_from(cues, probe(job.video).duration), engine, job)
    checkpoint()
    free_for_voice()
    stems = separate(job.video)
    samples = references(stems, words, job.cache / "voices")
    checkpoint()
    speech = speak(engine, job, samples, lines)
    checkpoint()
    sound = write_wav(job.cache / f"dub.{job.target}.wav", mix(lines, speech, stems.background))
    return mux(picture, sound, job.output(".dub.mp4"))
