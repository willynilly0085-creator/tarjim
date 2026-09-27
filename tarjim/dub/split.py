"""Cut one long voice recording back into its lines, using the word aligner to find each seam."""
from itertools import pairwise

import numpy as np

from tarjim.dub.audio import RATE, resample

ALIGN_RATE = 16000


def line_ends(words: list[tuple[float, float]], counts: list[int]) -> list[float]:
    seams, index = [], 0
    for count in counts[:-1]:
        index += count
        last_end, next_start = words[index - 1][1], words[index][0]
        seams.append((last_end + next_start) / 2)
    return seams


def word_times(wav: np.ndarray, texts: list[str], language: str) -> list[tuple[float, float]]:
    from tarjim.asr.align import shared_aligner
    from tarjim.listen.gemini_listen import Utterance

    heard = resample(wav, RATE, ALIGN_RATE)
    total = heard.size / ALIGN_RATE
    utterances = [Utterance(0.0, total, "", text) for text in texts]
    return [(w.start, w.end) for w in shared_aligner().align(heard, utterances, language)]


def split_lines(wav: np.ndarray, texts: list[str], language: str) -> list[np.ndarray]:
    if len(texts) == 1:
        return [wav]
    counts = [len(text.split()) for text in texts]
    words = word_times(wav, texts, language)
    if len(words) != sum(counts):
        return []
    seams = [0, *[round(t * RATE) for t in line_ends(words, counts)], wav.size]
    return [wav[a:b] for a, b in pairwise(seams)]
