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


def listen_and_align(job: Job, audio: Path, heard: Heard,
                     report: Callable[[str], None]) -> tuple[Transcript, bool]:
    """The transcript, and whether it covers all the speech, so it is worth keeping."""
    import soundfile

    from tarjim import hearing
    from tarjim.listen import check, settle
    from tarjim.listen.opinion import sounded
    from tarjim.listen.whose import by_voice

    report("timing")
    wav, rate = soundfile.read(str(audio), dtype="float32")
    # first: its times correct a cloud listener's drift; the local listener is its own. Since
    # 2026-11-08 its words are used only where the sound confirms them (listen/opinion.sounded)
    local = heard.local_words
    opinion = hearing.second_opinion(audio, heard.language) if local is None else local
    opinion = sounded(opinion, wav)
    done = settle.settled(job, heard, settle.Sound(wav, rate, check.regions_in(wav)), opinion)
    # shown on the job, the stretches given up too (2026-11-08)
    findings().heard(tuple((g.start, g.end) for g in done.left if not g.given_up),
                     done.agreement, tuple((g.start, g.end) for g in done.left if g.given_up))
    words = by_voice(done.transcript.words, wav, rate)
    return replace(done.transcript, words=words), done.whole and not heard.backup
