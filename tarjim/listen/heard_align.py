"""A cloud hearing's lines timed on the clip's sound, with the words this computer heard as the
second opinion, then each word given to its speaker by voice. Moved out of hearing.py on 2026-11-08,
unchanged, to make room there; hearing.py still offers it. The second opinion is reached through
the hearing module, as are the settle and check steps through theirs, so what tests and the bench
put in place of them there is what runs."""
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from tarjim.asr.base import Transcript
from tarjim.findings import findings
from tarjim.job import Job
from tarjim.listen.merge import Heard
from tarjim.prefs.active import active


def listen_and_align(job: Job, audio: Path, heard: Heard,
                     report: Callable[[str], None]) -> tuple[Transcript, bool]:
    """The transcript, and whether it covers all the speech, so it is worth keeping."""
    import soundfile

    from tarjim import hearing
    from tarjim.listen import check, settle
    from tarjim.listen.opinion import doubted, sounded
    from tarjim.listen.whose import by_voice

    report("timing")
    wav, rate = soundfile.read(str(audio), dtype="float32")
    # first: its times correct a cloud listener's drift; the local listener is its own. Since
    # 2026-11-08 its words are used only where the sound confirms them (listen/opinion.sounded)
    local, chosen = heard.local_words, active().listen
    # turned off, a weak computer times on the sound alone, faster and less exactly (2026-11-09)
    opinion = local
    if opinion is None:
        opinion = hearing.second_opinion(audio, heard.language) if chosen.second_opinion else []
    kept = sounded(opinion, wav)
    sound = settle.Sound(wav, rate, check.regions_in(wav), doubted(opinion, kept))
    done = settle.settled(job, heard, sound, kept)
    # shown on the job, the stretches given up too (2026-11-08)
    findings().heard(tuple((g.start, g.end) for g in done.left if not g.given_up),
                     done.agreement, tuple((g.start, g.end) for g in done.left if g.given_up))
    # turned off, the speakers stay as the listener heard them and no voice print is fetched
    words = done.transcript.words
    if chosen.voice_check:
        words = by_voice(words, wav, rate)
    return replace(done.transcript, words=words), done.whole and not heard.backup
