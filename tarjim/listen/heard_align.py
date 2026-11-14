"""A cloud hearing's lines timed on the clip's sound, with the words this computer heard as the
second opinion, then each word given to its speaker by voice. Moved out of hearing.py on 2026-11-08
to make room there; hearing.py still offers it. Since 2026-11-09 every timing reads one map of
the clip's speech (listen/clipmap.py), and every hearing leaves that map (`mapped`). The second
opinion is reached through the hearing module, as are the settle and check steps through theirs,
so what tests and the bench put in place of them there is what runs."""
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any, NamedTuple

from tarjim.asr.base import Transcript
from tarjim.findings import findings
from tarjim.job import Job
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard
from tarjim.models import Word
from tarjim.prefs.active import active

OWN_WORDS = ("local", "words")  # the requests of lines made of the local listener's words


def listen_and_align(job: Job, audio: Path, heard: Heard,
                     report: Callable[[str], None]) -> tuple[Transcript, bool]:
    """The transcript, and whether it covers all the speech, so it is worth keeping."""
    import soundfile

    from tarjim.listen import settle
    from tarjim.listen.clipmap import Clip, clip_map
    from tarjim.listen.opinion import backing, doubted, held, sounded

    report("timing")
    wav, rate = soundfile.read(str(audio), dtype="float32")
    opinion = second_opinion(audio, heard)
    kept = sounded(opinion, wav)
    # one map of the clip's speech for every timing, the detector run once (2026-11-09)
    lines = [(u.start, u.end) for u in heard.utterances]
    speech = clip_map(job.cache, Clip(audio, wav, rate), lines)
    # the passes judged by all the local words' text, a fill by the ones kept words hold in
    # place (listen/opinion.backing and held, 2026-11-09)
    sound = settle.Sound(wav, rate, speech.speech(), doubted(opinion, kept),
                         backing(opinion, kept), held(opinion, kept), speech_map=speech)
    done = settle.settled(job, heard, sound, kept)
    # shown on the job, the stretches given up too (2026-11-08)
    findings().heard(tuple((g.start, g.end) for g in done.left if not g.given_up),
                     done.agreement, tuple((g.start, g.end) for g in done.left if g.given_up))
    # who wrote each word (listen/witness.py, 2026-11-14): the passes, what asking again brought
    # (a fill made of the local words is the local listener's own), and the local listener,
    # which is no witness to its own hearing
    second = backing(opinion, kept) if heard.local_words is None else []
    again = [fill.line for fill in done.fills if fill.line.request not in OWN_WORDS]
    words = final_words(done.transcript.words, (wav, rate), Witnesses(heard.passes, second, again))
    return replace(done.transcript, words=words), done.whole and not heard.backup


class Witnesses(NamedTuple):
    passes: list[list[Utterance]]
    local: list[Word]
    again: list[Utterance]


def final_words(words: list[Word], sound: tuple[Any, int], who: Witnesses) -> list[Word]:
    """The words as shown: each given to its speaker by voice (turned off, the speakers stay as
    the listener heard them and no voice print is fetched), then each run's strict score read
    once, their speakers final (2026-11-09), then who wrote each word (2026-11-14)."""
    from tarjim.listen.timing import final_scores
    from tarjim.listen.whose import by_voice
    from tarjim.listen.witness import witnessed

    wav, rate = sound
    if active().listen.voice_check:
        words = by_voice(words, wav, rate)
    return witnessed(final_scores(wav, words), who.passes, who.local, who.again)


def second_opinion(audio: Path, heard: Heard) -> list[Word]:
    """First: its times correct a cloud listener's drift; the local listener is its own. Since
    2026-11-08 its words are used only where the sound confirms them (listen/opinion.sounded).
    Turned off, a weak computer times on the sound alone, faster and less exactly (2026-11-09)."""
    from tarjim import hearing

    if heard.local_words is not None:
        return heard.local_words
    return hearing.second_opinion(audio, heard.language) if active().listen.second_opinion else []


def mapped(job: Job, audio: Path, result: tuple[Transcript, bool]) -> tuple[Transcript, bool]:
    """A hearing's result, the clip's speech map kept beside it whichever way it was heard
    (2026-11-09: only the lines timed here made one, so the local listener's transcript and a
    hearing with no speech left none)."""
    from tarjim.listen.clipmap import untimed_map

    untimed_map(job.cache, audio)
    return result
