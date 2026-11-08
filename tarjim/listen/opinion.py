"""The words this computer heard count only when they are in the language the clip was heard in.

On 2026-11-08 a Somali army chant came out twice over and twenty seconds early. The listener on
this computer (Qwen3-ASR) knows about thirty languages, and Somali is not one of them: it took the
chant for Arabic and wrote Arabic-looking words that mean nothing. Their times then moved the
cloud listener's lines, the coverage check took them for speech the cloud listener had missed and
put 142 of them in, and the timing that came out was spread evenly over the whole clip. Words in
another language than the one heard are not a second opinion on what was said, so none of them
are used: the aligner times the cloud listener's own lines on the sound alone, as it always can.
"""
from tarjim.models import Word
from tarjim.translate.glossary import language_code


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
