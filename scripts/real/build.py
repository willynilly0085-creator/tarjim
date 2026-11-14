"""Clips made of real recorded sentences, with the truth each of the three measures needs.

A clip is FLEURS sentences (fetch.py) one after another. What was said and its translation by a
person come with each sentence; when it is said comes from how the clip was put together: each
recording is trimmed to its own speech and laid at a known time, so a sentence's start and end
are known without any aligner (tarjim's own aligner would be judging itself). Where the speech
of a recording begins and ends inside it is measured twice, by its loudness against its own room
noise and by the voice detector; an edge the two put more than AGREE apart is marked unsure and
no timing is scored on it (2026-11-14: taken from loudness alone, with a bar under the room's
noise, every sentence "began" up to a second before its first word). Around that:
pauses of seeded length, a second voice in turns, turns with hardly a pause, voices over one
another, pink noise or a music bed under the speech, and a clip long enough to be heard in
several pieces. All of it is read speech from an encyclopedia's sentences: free talk, laughter
and real songs are not in it.

    python build.py            every recipe of RECIPES whose material is fetched
    python build.py --truth    only the truth of each clip again, its sound left as it is
"""
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import soundfile
from paths import CLIPS, MATERIAL, RATE, REPO, prepare

prepare()
sys.path.append(str(REPO / "scripts" / "synth"))
from beds import bed  # noqa: E402
from edges import edges  # noqa: E402

LEVEL = 0.06  # the loudness every sentence is brought to (RMS)
QUIET = 35.0  # dB under a recording's loudest frame that is still its speech
EDGE = 0.05  # seconds kept either side of a recording's speech
HOP = RATE // 100
TARGETS = {"ar_eg": "ar", "en_us": "en"}
Row = dict[str, Any]


@dataclass(frozen=True)
class Recipe:
    name: str
    language: str
    sentences: int = 8
    skip: int = 0  # sentences of the language left to the recipes before this one
    gap: tuple[float, float] = (0.6, 1.4)  # seconds between two sentences
    bed: str = ""  # "noise" or "music" under the speech
    snr: float = 5.0  # dB the speech is above the bed
    turns: bool = False  # a man's and a woman's recordings in turns
    over: float = 0.0  # seconds each sentence begins before the one before it ends

    @property
    def reference(self) -> str:
        return "en_us" if self.language == "ar_eg" else "ar_eg"


CLEAN = ("en_us", "ar_eg", "fr_fr", "es_419", "de_de", "ru_ru", "tr_tr", "ja_jp", "cmn_hans_cn",
         "hi_in", "ko_kr", "id_id", "fa_ir", "pt_br", "ur_pk")
RECIPES = [
    *(Recipe(f"{language}_clean", language) for language in CLEAN),
    Recipe("en_us_noise", "en_us", skip=8, bed="noise"),
    Recipe("en_us_music", "en_us", skip=16, bed="music"),
    Recipe("en_us_turns", "en_us", skip=24, gap=(0.25, 0.5), turns=True),
    Recipe("en_us_fast", "en_us", skip=32, gap=(0.08, 0.2), turns=True),
    Recipe("en_us_over", "en_us", skip=40, turns=True, over=0.8),
    Recipe("en_us_long", "en_us", sentences=45),
    Recipe("ar_eg_noise", "ar_eg", skip=8, bed="noise"),
    Recipe("ar_eg_long", "ar_eg", sentences=24),
    Recipe("fr_fr_music", "fr_fr", sentences=8, skip=4, bed="music"),
]


def spoken(path: Path) -> np.ndarray:
    """A recording's own speech, EDGE either side, at the level every sentence has."""
    wav, rate = soundfile.read(str(path), dtype="float32", always_2d=True)
    assert rate == RATE, (path, rate)
    mono = wav.mean(axis=1)
    frames = mono[:len(mono) // HOP * HOP].reshape(-1, HOP).astype(np.float64)
    loud = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-9)
    heard = np.flatnonzero(loud > loud.max() - QUIET)
    low = max(0, int(heard[0] * HOP - EDGE * RATE))
    high = min(len(mono), int((heard[-1] + 1) * HOP + EDGE * RATE))
    cut = mono[low:high]
    return np.asarray(cut * (LEVEL / (np.sqrt((cut ** 2).mean()) + 1e-9)), dtype=np.float32)


def material(language: str) -> list[tuple[Row, Path]]:
    """The sentences fetched for the language, in the order they were fetched."""
    rows = json.loads((MATERIAL / language / "rows.json").read_text(encoding="utf-8"))
    found = [(row, MATERIAL / language / f"{row['id']}-{index}.wav")
             for index, row in enumerate(rows)]
    return [(row, path) for row, path in found if path.exists()]


def in_turns(pool: list[tuple[Row, Path]]) -> list[tuple[Row, Path]]:
    """A man's and a woman's recordings one after the other, while both are left."""
    men = [item for item in pool if item[0]["gender"] == 0]
    women = [item for item in pool if item[0]["gender"] != 0]
    paired = [item for pair in zip(men, women, strict=False) for item in pair]
    return paired or pool


def chosen(recipe: Recipe) -> list[tuple[Row, Path]]:
    pool = material(recipe.language)[recipe.skip:]
    picked = (in_turns(pool) if recipe.turns else pool)[:recipe.sentences]
    assert len(picked) == recipe.sentences, (recipe.name, len(picked))
    return picked


def references(language: str) -> dict[int, str]:
    rows = json.loads((MATERIAL / language / "rows.json").read_text(encoding="utf-8"))
    return {int(row["id"]): str(row["raw_transcription"]) for row in rows}


def laid(recipe: Recipe, rng: np.random.Generator) -> tuple[np.ndarray, list[Row]]:
    """The sentences at their times, and the truth of each."""
    meant, cursor, parts, truth = references(recipe.reference), 1.0, [], []
    for row, path in chosen(recipe):
        voice = spoken(path)
        start = max(0.0, cursor - recipe.over) if truth else cursor
        parts.append((int(start * RATE), voice))
        end, edge = start + len(voice) / RATE, edges(voice)
        truth.append({"id": row["id"], "text": row["raw_transcription"],
                      "reference": meant[int(row["id"])],
                      "speaker": "S1" if row["gender"] == 0 or not recipe.turns else "S2",
                      "start": round(start + edge["low"], 3),
                      "end": round(start + edge["high"], 3),
                      "sure_start": bool(edge["sure_start"]), "sure_end": bool(edge["sure_end"])})
        cursor = end + float(rng.uniform(*recipe.gap)) if not recipe.over else end
    sound = np.zeros(int((cursor + 1.0) * RATE), dtype=np.float32)
    for at, voice in parts:
        sound[at:at + len(voice)] += voice
    return sound, truth


def under(sound: np.ndarray, recipe: Recipe) -> np.ndarray:
    """The speech with the recipe's bed under it, the speech `snr` dB above it."""
    if not recipe.bed:
        return sound
    below = bed(recipe.bed, len(sound)).astype(np.float32)
    level = LEVEL / (10 ** (recipe.snr / 20))
    return sound + below * (level / (np.sqrt((below ** 2).mean()) + 1e-9))


def build(recipe: Recipe, sound_too: bool = True) -> Path:
    folder = CLIPS / recipe.name
    folder.mkdir(parents=True, exist_ok=True)
    sound, truth = laid(recipe, np.random.default_rng(len(recipe.name) * 7919))
    mixed = np.clip(under(sound, recipe), -1.0, 1.0)
    if sound_too:
        soundfile.write(str(folder / "clip.wav"), mixed, RATE, subtype="PCM_16")
    facts = {**asdict(recipe), "target": TARGETS[recipe.reference], "reference": recipe.reference,
             "duration": round(len(mixed) / RATE, 2), "sentences": truth}
    draft = folder / "truth.json.part"
    draft.write_text(json.dumps(facts, ensure_ascii=False, indent=1), encoding="utf-8")
    draft.replace(folder / "truth.json")  # whole or not at all: a run may be reading it
    return folder


def main() -> None:
    for recipe in RECIPES:
        try:
            there = (CLIPS / recipe.name / "clip.wav").exists()
            folder = build(recipe, "--truth" not in sys.argv or not there)
        except (OSError, AssertionError) as error:
            print(f"{recipe.name}: not built ({type(error).__name__}: {error})", flush=True)
            continue
        facts = json.loads((folder / "truth.json").read_text(encoding="utf-8"))
        sure = sum(s["sure_start"] + s["sure_end"] for s in facts["sentences"])
        print(f"{recipe.name}: {facts['duration']} s, {len(facts['sentences'])} sentences, "
              f"{sure} of {2 * len(facts['sentences'])} edges sure", flush=True)


if __name__ == "__main__":
    main()
