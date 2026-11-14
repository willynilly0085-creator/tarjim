"""Whether each speaker's voice is a man's or a woman's, measured from the sound (2026-11-14).

A translation into a language that marks gender has to know who is speaking: "I'm the design
director" is one word in Arabic for a man and another for a woman. An engine that only reads the
lines guessed from the name, and a man called Andrea became a woman, in the subtitles and in the
summary made from them. The voice is measured here, on this computer, for every engine: the
pitch of what each speaker said, the same measure the dubbing voices are cast by.

A pitch between the two bands says nothing and nothing is claimed for it; a high voice may be a
child's, so it is given as such. No failure here fails a job: without it the lines are translated
as they were before.
"""
import tempfile
from pathlib import Path
from typing import Any

import numpy as np

from tarjim.models import Word
from tarjim.speakers import who

RATE = 16000
PITCH_RANGE = (60.0, 400.0)
# A man's voice mostly sits at 85-155 Hz and a woman's at 165-255 Hz; between them it is not said.
LOW_BELOW, HIGH_ABOVE = 150.0, 185.0
ENOUGH, MOST = 3.0, 30.0  # seconds of a speaker's own words: fewer are not judged
LOW, HIGH = "low", "high"
Voices = tuple[tuple[str, str], ...]  # each speaker's label ("" when there are no labels) and voice


def pitch(samples: np.ndarray) -> float:
    import librosa

    low, high = PITCH_RANGE
    track = librosa.yin(samples, fmin=low, fmax=high, sr=RATE)
    voiced = track[(track > low) & (track < high)]
    return float(np.median(voiced)) if voiced.size else 0.0


def kind(hertz: float) -> str:
    if 0.0 < hertz < LOW_BELOW:
        return LOW
    return HIGH if hertz > HIGH_ABOVE else ""


def said(words: list[Word], wav: np.ndarray) -> dict[str, np.ndarray]:
    """Each speaker's own words, joined: up to MOST seconds of them."""
    pieces: dict[str, list[np.ndarray]] = {}
    for word in words:
        mine = pieces.setdefault(who(word.speaker), [])
        if sum(len(piece) for piece in mine) < MOST * RATE:
            mine.append(wav[int(word.start * RATE):int(word.end * RATE)])
    return {label: np.concatenate(found) for label, found in pieces.items() if found}


def measured(words: list[Word], wav: np.ndarray) -> Voices:
    found = []
    for label, samples in sorted(said(words, wav).items()):
        voice = kind(pitch(samples)) if len(samples) >= ENOUGH * RATE else ""
        if voice:
            found.append((label, voice))
    return tuple(found)


def voices_of(video: Path, words: list[Word]) -> Voices:
    """The voices of a clip's speakers; none when the sound cannot be read or measured."""
    from tarjim import media

    try:
        import soundfile

        with tempfile.TemporaryDirectory(prefix="tarjim-voices-") as folder:
            sound = Path(folder) / "sound.wav"
            media.extract_audio(video, sound)
            wav, rate = soundfile.read(str(sound), dtype="float32")
        if rate != RATE or not len(wav):
            return ()
        found = measured(words, wav if wav.ndim == 1 else wav.mean(axis=1))
    except Exception as error:  # never a reason to stop a translation
        print(f"voices: not measured ({type(error).__name__}: {str(error)[:160]})", flush=True)
        return ()
    if found:
        print("voices: " + ", ".join(f"{label or 'the speaker'} {voice}" for label, voice in found),
              flush=True)
    return found


def told(voices: Voices, key: str) -> str:
    """The lines a prompt carries about the voices, in the prompt's language; "" for none."""
    if not voices:
        return ""
    names: dict[str, Any] = PHRASES[key]
    listed = "; ".join(f"{label or names['alone']}: {names[voice]}" for label, voice in voices)
    return str(names["lead"]).format(voices=listed)


PHRASES: dict[str, dict[str, str]] = {
    "ar": {"alone": "المتكلم", LOW: "صوت رجل", HIGH: "صوت امرأة (أو طفل)",
           "lead": "\n\nأصوات المتكلمين، مقاسة من صوت المقطع نفسه: {voices}. اعتمد عليها في "
                   "التذكير والتأنيث لما المتكلم يتكلم عن نفسه أو يخاطبه أحد، ولا تحكم على جنس "
                   "أحد من اسمه أبداً. المتكلم اللي ما انذكر صوته هنا لا تفترض جنسه."},
    "any": {"alone": "the speaker", LOW: "a man's voice", HIGH: "a woman's voice (or a child's)",
            "lead": "\n\nThe speakers' voices, measured from the clip's own sound: {voices}. Use "
                    "them for grammatical gender when a speaker talks about themself or is "
                    "spoken to, and never judge anyone's gender from a name. Assume no gender "
                    "for a speaker whose voice is not listed here."},
}
