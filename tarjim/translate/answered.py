"""Which model translated a job, against the one the person picked (2026-11-19).

Until then a picked Gemini model the key refused (gemini_client.REFUSED) handed its lines to the
next model of the usual list, a picked Antigravity effort that failed handed them to its low
variant, a Codex model the account refused to the next one, and an engine that failed to the
backup, and only the job's log said so. The page and the extension kept naming the picked model,
so a person believed it had translated their video. The job now lists what did (findings.py,
"other_model"), named as the page names models.
"""
from typing import Protocol

from tarjim.config import setting
from tarjim.engines.catalog import BY_ID
from tarjim.engines.model_catalog import pretty
from tarjim.findings import findings
from tarjim.models import Cue


class Wrote(Protocol):
    answered: list[str]  # the models whose answers gave lines, in order (translate/gemini.py)


def named(provider: str, model: str) -> str:
    """A model as the page names it, or the engine itself when it runs its own default."""
    if model:
        return pretty(model)
    known = BY_ID.get(provider)
    return known.name if known else provider


def picked_by_person(provider: str) -> str:
    """The model picked for the job's chosen engine, kept on the job; read before the engine
    runs, since Codex saves the model that answered as the new pick."""
    chosen = setting(f"{provider}_model")
    findings().picked = named(provider, chosen)
    return chosen


def others(models: list[str], chosen: str | None, wrote: bool) -> list[str]:
    """The chosen engine (chosen is its pick) counts only a model other than a picked one; a
    backup (None) counts once it wrote a line, by the models it named or by its own pick."""
    if chosen is not None:
        return [model for model in models if chosen and model != chosen]
    return (models or [""]) if wrote else []


def said(provider: str, translator: Wrote, wanted: list[Cue], chosen: str | None) -> None:
    """Which engine wrote the lines, in the job's log (2026-11-14: it said nothing, and a
    translation by a weaker model after a failure looked like the chosen one's), and on the job
    when that is not what the person picked."""
    models = translator.answered
    done = sum(1 for cue in wanted if cue.text.strip())
    print(f"translation: {done} of {len(wanted)} line(s) by {provider}"
          + (f" ({', '.join(models)})" if models else ""), flush=True)
    found = findings()
    for model in others(models, chosen, done > 0):
        name = named(provider, model or setting(f"{provider}_model"))
        if name not in found.in_place:
            found.in_place.append(name)
