"""A cloud hearing's lines timed on the clip's sound, with the words this computer heard as the
second opinion, then each word given to its speaker by voice. Moved out of hearing.py on 2026-11-08
to make room there; hearing.py still offers it. Since 2026-11-09 every timing reads one map of
the clip's speech (listen/clipmap.py), and every hearing leaves that map (`mapped`). The second
opinion is reached through the hearing module, as are the settle and check steps through theirs,
so what tests and the bench put in place of them there is what runs."""
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from tarjim.asr.base import Transcript
from tarjim.findings import findings
from tarjim.job import Job
from tarjim.listen.merge import Heard
from tarjim.models import Word
from tarjim.prefs.active import active


def listen_and_align(job: Job, audio: Path, heard: Heard,
                     report: Callable[[str], None]) -> tuple[Transcript, bool]:
    """The transcript, and whether it covers all the speech, so it is worth keeping."""
    import soundfile

    from tarjim.listen import settle
    from tarjim.listen.clipmap import Clip, clip_map
    from tarjim.listen.opinion import doubted, sounded
    from tarjim.listen.timing import final_scores
    from tarjim.listen.whose import by_voice

    report("timing")
    wav, rate = soundfile.read(str(audio), dtype="float32")
    chosen = active().listen
    opinion = second_opinion(audio, heard)
    kept = sounded(opinion, wav)
    # one map of the clip's speech for every timing, the detector run once (2026-11-09)
    lines = [(u.start, u.end) for u in heard.utterances]
    speech = clip_map(job.cache, Clip(audio, wav, rate), lines)
    sound = settle.Sound(wav, rate, speech.speech(), doubted(opinion, kept), speech)
    done = settle.settled(job, heard, sound, kept)
    # shown on the job, the stretches given up too (2026-11-08)
    findings().heard(tuple((g.start, g.end) for g in done.left if not g.given_up),
                     done.agreement, tuple((g.start, g.end) for g in done.left if g.given_up))
    # turned off, the speakers stay as the listener heard them and no voice print is fetched
    words = by_voice(done.transcript.words, wav, rate) if chosen.voice_check \
        else done.transcript.words
    # each run's strict score, read once on the words as shown, their speakers final (2026-11-09)
    words = final_scores(wav, words)
    return replace(done.transcript, words=words), done.whole and not heard.backup


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
