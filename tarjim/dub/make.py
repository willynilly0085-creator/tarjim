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
from tarjim.job import Job
from tarjim.media import probe
from tarjim.models import Cue, Word

SAVED_VOICE = "fish:saved"
FIRST_SECONDS = 10.0
SAFE = re.compile(r"[^\w.-]")
NUMBER = re.compile(r"\d+")


class DubUnavailable(RuntimeError):
    pass


class Voices(Protocol):
    def speak_all(self, lines: list[Line]) -> list[np.ndarray]: ...


def choose(engine: str, language: str) -> str:
    wanted = engine.split(":", maxsplit=1)[0]
    if wanted == "fish" and not setting("fish_api_key"):
        wanted = "clone"
    if wanted == "studio" and language not in VOICES:
        wanted = "clone"
    if wanted == "clone" and language not in CLONE_LANGUAGES:
        wanted = "studio" if language in VOICES else ""
    if not wanted:
        raise DubUnavailable(f"no dubbing voice for language {language}")
    return wanted


def references(stems: Stems, words: list[Word], folder: Path) -> dict[str, Path]:
    folder.mkdir(parents=True, exist_ok=True)
    spans = {k: v for k, v in reference_spans(words).items() if v} or {"": [(0.0, FIRST_SECONDS)]}
    return {speaker: write_wav(folder / f"{SAFE.sub('_', speaker) or 'voice'}.wav",
                               cut(stems.voices, chosen))
            for speaker, chosen in spans.items()}


def voices_for(engine: str, spec: str, job: Job, samples: dict[str, Path]) -> Voices:
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


def spoken(lines: list[Line], engine: str, language: str) -> list[Line]:
    if engine == "studio":
        return lines
    texts = [spell_numbers(line.text, language) for line in lines]
    if language == "ar":
        from tarjim.dub.tashkeel import add_vowels

        texts = add_vowels(texts)
    return [Line(line.start, line.until, line.speaker, text) for line, text in zip(lines, texts,
                                                                                   strict=True)]


def dub_video(job: Job, cues: list[Cue], words: list[Word], picture: Path) -> Path:
    engine = choose(job.dub, job.target)
    lines = spoken(lines_from(cues, probe(job.video).duration), engine, job.target)
    stems = separate(job.video)
    samples = references(stems, words, job.cache / "voices")
    speech = voices_for(engine, job.dub, job, samples).speak_all(lines)
    sound = write_wav(job.cache / f"dub.{job.target}.wav", mix(lines, speech, stems.background))
    return mux(picture, sound, job.output(".dub.mp4"))
