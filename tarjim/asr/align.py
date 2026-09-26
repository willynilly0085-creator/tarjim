from typing import Any

from tarjim.asr.qwen import ALIGNER_MODEL, attach_punctuation, core
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

SAMPLE_RATE = 16000
CHUNK_SECONDS = 240.0
PAD = 2.0
MIN_COVERAGE = 0.8


def proportional(utterance: Utterance) -> list[Word]:
    tokens = utterance.text.split()
    weights = [max(1, len(core(token))) for token in tokens]
    step = (utterance.end - utterance.start) / max(1, sum(weights))
    words, cursor = [], utterance.start
    for token, weight in zip(tokens, weights, strict=True):
        words.append(Word(token, cursor, cursor + weight * step, utterance.speaker))
        cursor += weight * step
    return words


def chunks(utterances: list[Utterance]) -> list[list[Utterance]]:
    groups: list[list[Utterance]] = []
    for utterance in utterances:
        if groups and utterance.end - groups[-1][0].start <= CHUNK_SECONDS:
            groups[-1].append(utterance)
        else:
            groups.append([utterance])
    return groups


def speakers_by_token(utterances: list[Utterance]) -> list[str]:
    return [u.speaker for u in utterances for token in u.text.split() if core(token)]


class AlignEngine:
    def __init__(self, device: str = "cuda:0") -> None:
        import torch
        from qwen_asr import Qwen3ForcedAligner

        self.aligner = Qwen3ForcedAligner.from_pretrained(
            ALIGNER_MODEL, dtype=torch.bfloat16, device_map=device)
        supported = self.aligner.get_supported_languages() or []
        self.languages = {name.lower() for name in supported}

    def align(self, wav: Any, utterances: list[Utterance], language: str) -> list[Word]:
        if language.lower() not in self.languages:
            return [word for u in utterances for word in proportional(u)]
        return [w for group in chunks(utterances) for w in self.align_chunk(wav, group, language)]

    def align_chunk(self, wav: Any, group: list[Utterance], language: str) -> list[Word]:
        low = max(0.0, group[0].start - PAD)
        high = min(len(wav) / SAMPLE_RATE, max(u.end for u in group) + PAD)
        text = " ".join(u.text for u in group)
        clip = wav[int(low * SAMPLE_RATE):int(high * SAMPLE_RATE)]
        try:
            items = list(self.aligner.align(audio=(clip, SAMPLE_RATE), text=text,
                                            language=language)[0])
        except (RuntimeError, ValueError):
            return [word for u in group for word in proportional(u)]
        words = attach_punctuation(text, items)
        speakers = speakers_by_token(group)
        if len(words) < MIN_COVERAGE * len(speakers):
            return [word for u in group for word in proportional(u)]
        return [Word(w.text, low + w.start, low + w.end, speakers[min(i, len(speakers) - 1)])
                for i, w in enumerate(words)]
