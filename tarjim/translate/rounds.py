"""Every engine of the chain is tried while a line with words is still untranslated.

Until 2026-11-08 the first engine that did not fail outright ended the translation, so a line it
left empty never reached the backup and the speech went without a subtitle. Now each engine gets
only the lines still empty, and after the last one a line no engine translated shows the words
as they were said, and is listed on the job (findings.py). Text longer than its time allows is
kept and listed as a readability warning: a long answer is a fit problem, not a wrong one, and a
backup asked for it would give a worse line at more cost.
"""
from tarjim.findings import findings
from tarjim.job import checkpoint
from tarjim.models import Cue
from tarjim.rules import Rules
from tarjim.translate.clean import over_budget
from tarjim.translate.gemini import BAD_REPLY, AudioSlice, Translator
from tarjim.translate.prompt import Brief
from tarjim.translate.slots import as_said, has_letters

# An engine that cannot be made (a key removed, a local server gone, a library missing) hands
# over to the backup like one that failed.
UNBUILT = (*BAD_REPLY, OSError, ImportError)


class Rounds:
    def __init__(self, cues: list[Cue], audio: AudioSlice, brief: Brief) -> None:
        self.cues, self.audio, self.brief = cues, audio, brief
        self.sounds: set[int] = set()  # lines (by id) an engine answered empty as only a sound
        # the parts each line was asked in (prompt.format_item), before one_speaker merges the
        # parts of an exchange answered as one sentence
        self.parts = [len(cue.parts) for cue in cues]
        self.stopped: list[Exception] = []  # what the last engine that ran failed on

    def pending(self) -> list[Cue]:
        return [cue for cue in self.cues if not cue.text.strip() and has_letters(cue.source)
                and id(cue) not in self.sounds]

    def run(self) -> list[Exception]:
        """The failures met on the way; what an engine filled before failing stays, so a used-up
        quota on the backup never takes back what the first engine did."""
        from tarjim.engines.choice import tried
        from tarjim.prefs.active import active

        failures: list[Exception] = []
        wanted = [cue for cue in self.cues if not cue.text.strip()]  # a backup never redoes good
        for turn, provider in enumerate(tried("translate", active().translate.local_backup)):
            if not wanted:
                break
            checkpoint()  # a backup engine is never started for a job that was cancelled
            failures += self.turn(provider, wanted, self.cues if turn else None)
            wanted = self.pending()
        return failures

    def turn(self, provider: str, wanted: list[Cue], whole: list[Cue] | None) -> list[Exception]:
        """One engine's failures. Since 2026-11-08 an engine is made inside the try: a missing
        key no longer fails the job before the backup is tried, and a backup that cannot be made
        no longer throws away what the first engine translated. Only an engine that ran is the
        one the stop note speaks of (stopped)."""
        from tarjim.engines.choice import asker

        try:
            translator = Translator(asker(provider), whole)
        except UNBUILT as error:
            print(f"translation: {provider} could not be started: {error}", flush=True)
            return [error]
        try:
            translator.translate(wanted, self.audio, self.brief)
        except BAD_REPLY as error:
            translator.failures.append(error)
        self.sounds |= translator.sounds
        self.stopped = translator.failures
        # which engine wrote the lines, in the job's log (2026-11-14: it said nothing, and a
        # translation by a weaker model after a failure looked like the chosen one's)
        model = str(getattr(translator.client, "model_used", "") or "")
        done = sum(1 for cue in wanted if cue.text.strip())
        print(f"translation: {done} of {len(wanted)} line(s) by {provider}"
              + (f" ({model})" if model else ""), flush=True)
        return translator.failures

    def translated(self) -> bool:
        return any(cue.text.strip() for cue in self.cues)

    def finish(self, rules: Rules) -> None:
        """The last resort for what is still empty, and what is written down for the job."""
        found = findings()
        still = {id(cue) for cue in self.pending()}
        for number, cue in enumerate(self.cues, start=1):
            if id(cue) in still:
                cue.text = as_said(cue)
                found.in_source.append(number)
            elif id(cue) in self.sounds and not cue.text.strip():
                found.sounds.append(number)
        if found.in_source:
            print(f"translation: {len(found.in_source)} line(s) came back from no engine; "
                  "shown as they were said", flush=True)
        shown = set(found.in_source)
        texts = {n: cue.text for n, cue in enumerate(self.cues, start=1)
                 if cue.text.strip() and n not in shown}
        budgets = [rules.budgets(cue.duration, parts) for cue, parts in zip(self.cues, self.parts,
                                                                               strict=True)]
        found.over_budget = over_budget(texts, budgets)
