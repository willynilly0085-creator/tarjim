"""The words this computer heard count only when they are in the language the clip was heard in.

On 2026-11-08 a Somali army chant came out twice over and twenty seconds early. The listener on
this computer (Qwen3-ASR) knows about thirty languages, and Somali is not one of them: it took the
chant for Arabic and wrote Arabic-looking words that mean nothing. Their times then moved the
cloud listener's lines, the coverage check took them for speech the cloud listener had missed and
put 142 of them in, and the timing that came out was spread evenly over the whole clip. Words in
another language than the one heard are not a second opinion on what was said, so none of them
are used: the aligner times the cloud listener's own lines on the sound alone, as it always can.

Words in the right language can still be heard at the wrong times: since 2026-11-08 they are used
only where the sound confirms them (sounded, asr/confirm.py).
"""
from typing import TYPE_CHECKING, Any

from tarjim import guards
from tarjim.models import Word
from tarjim.translate.glossary import language_code

if TYPE_CHECKING:
    from tarjim.asr.confirm import Kept


def named(languages: str) -> set[str]:
    """Each language of a listener's answer ("English,Arabic"), as one comparable name."""
    return {language_code(part) for part in languages.split(",") if part.strip()}


def agreeing(words: list[Word], local: str, heard: str) -> list[Word]:
    """The local words when their language is the heard one (or either is unknown), else none."""
    if not words or not named(local) or not named(heard) or named(local) & named(heard):
        return words
    print(f"timing: the listener on this computer heard {local}, not {heard}; "
          f"its {len(words)} words are not used", flush=True)
    return []


def sounded(words: list[Word], wav: Any) -> list[Word]:
    """The local words the sound confirms where they are timed (asr/confirm.py, 2026-11-08), read
    from the letters the aligner hears in the whole clip once for timing anyway; what is left out
    is said once in the log and counted."""
    if not words:
        return words
    from tarjim.asr.align import shared_aligner
    from tarjim.asr.confirm import confirmed, unchecked
    from tarjim.memory import heavy

    with heavy():
        engine = shared_aligner()
        emitter = getattr(engine, "emitter", None)  # a stand-in aligner has no ears
        letters = None if emitter is None else emitter.emissions(wav)
    kept = unchecked(words) if letters is None else confirmed(letters, words, engine.tokens)
    told(kept)
    return kept.words


def told(kept: "Kept") -> None:
    guards.fired("opinion.no_length", kept.no_length)
    guards.fired("opinion.not_found", kept.not_found)
    guards.fired("opinion.stretch", kept.stretch)
    guards.fired("opinion.unused", kept.unused)
    print(said(kept), flush=True)


def said(kept: "Kept") -> str:
    heard = f"timing: of the {kept.heard} words the listener on this computer heard"
    if not kept.checked:
        return (f"{heard}, {len(kept.words)} are used unchecked (no letters to look for in the "
                f"sound); {kept.no_length} with no length that can be said are left out")
    if kept.unused:
        return (f"{heard}, none is used: hardly any was heard where it is timed "
                f"({kept.no_length} with no length that can be said)")
    return (f"{heard}, {len(kept.words)} are used where the sound confirms them; left out: "
            f"{kept.no_length} with no length that can be said, {kept.not_found} not heard where "
            f"they are timed, {kept.stretch} in stretches mostly not heard where timed")
