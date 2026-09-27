from pathlib import Path

from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

PAUSE = 0.7
ENDS = (".", "?", "!", "؟", "。", "？", "！")


def utterances_from(words: list[Word]) -> list[Utterance]:
    groups: list[list[Word]] = []
    for word in words:
        last = groups[-1] if groups else None
        if last and word.start - last[-1].end < PAUSE and not last[-1].text.endswith(ENDS):
            last.append(word)
        else:
            groups.append([word])
    return [Utterance(g[0].start, max(g[-1].end, g[0].start + 0.01), "",
                      " ".join(w.text for w in g)) for g in groups]


def listen_file(audio: Path) -> tuple[str, list[Utterance]]:
    from tarjim.asr.qwen import shared_engine

    transcript = shared_engine().transcribe(str(audio))
    return transcript.language, utterances_from(transcript.words)
