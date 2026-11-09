"""Every setting, in the page's order of tabs (2026-11-09)."""
from tarjim.prefs.spec import Spec
from tarjim.prefs.table_listen import LISTEN
from tarjim.prefs.table_look import LOOK
from tarjim.prefs.table_output import DUB, OUTPUT
from tarjim.prefs.table_text import TEXT, TIMING
from tarjim.prefs.table_translate import TRANSLATE

GROUPS = ("look", "text", "timing", "listen", "translate", "output", "dub")
SPECS: dict[str, Spec] = {s.key: s for s in (*LOOK, *TEXT, *TIMING, *LISTEN, *TRANSLATE,
                                             *OUTPUT, *DUB)}


def in_group(group: str) -> list[str]:
    return [key for key, spec in SPECS.items() if spec.group == group]


def defaults(target: str) -> dict[str, object]:
    return {key: spec.at(target).default for key, spec in SPECS.items()}
