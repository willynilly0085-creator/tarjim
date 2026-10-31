"""The hearing kept beside a clip's other work, so a re-run does not pay to listen again. A hearing
that left speech out is never kept, and "listen again" forgets what was kept."""
import json
from dataclasses import asdict
from pathlib import Path

from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import Heard, agreed
from tarjim.models import Word

HEARD = "heard.json"
TRANSCRIPT = "transcript.json"
MADE_FROM_IT = "cues.*.json"


def load_heard(cache: Path) -> Heard | None:
    kept = cache / HEARD
    if not kept.exists():
        return None
    data = json.loads(kept.read_text(encoding="utf-8"))
    words = data.get("local_words")
    passes = [[Utterance(**u) for u in run] for run in data.get("passes") or []]
    voted = agreed(passes) if passes else [Utterance(**u) for u in data["utterances"]]
    return Heard(data["language"], voted, passes,
                 None if words is None else [Word(**w) for w in words],
                 str(data.get("provider") or ""),
                 [Utterance(**u) for u in data.get("added") or []])


def keep_heard(cache: Path, heard: Heard) -> None:
    (cache / HEARD).write_text(json.dumps(asdict(heard), ensure_ascii=False, indent=1),
                               encoding="utf-8")


def forget(cache: Path) -> None:
    """What a "listen again" clears: the hearing, its transcript and the lines made from them."""
    gone = [p for p in [cache / HEARD, cache / TRANSCRIPT, *cache.glob(MADE_FROM_IT)]
            if p.exists()]
    for path in gone:
        path.unlink(missing_ok=True)
    print(f"listen again: cleared {len(gone)} kept file(s) for {cache.name}", flush=True)
