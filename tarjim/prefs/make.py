"""Short ways to write one row of the settings tables (2026-11-09)."""
from dataclasses import replace

from tarjim.prefs.spec import Local, Spec, Value

BASIC, ADVANCED = "basic", "advanced"


def on_off(key: str, label: str, default: bool, tier: str = BASIC) -> Spec:
    return Spec(key, label, "switch", default, tier=tier)


def amount(key: str, label: str, default: float, span: tuple[float, float, float]) -> Spec:
    """span: the lowest, the highest and the step (0 for any value between)."""
    low, high, step = span
    return Spec(key, label, "number", default, low, high, step, tier=ADVANCED)


def basic(spec: Spec) -> Spec:
    return replace(spec, tier=BASIC)


def pick(key: str, label: str, choices: tuple[Value, ...], tier: str = BASIC) -> Spec:
    """The first choice is the default."""
    return Spec(key, label, "choice", choices[0], choices=choices, tier=tier)


def paint(key: str, label: str, default: str, tier: str = BASIC) -> Spec:
    return Spec(key, label, "colour", default, tier=tier)


def per_language(key: str, label: str, kind: str, local: Local) -> Spec:
    """Kept for each target language; the bare row holds Arabic's default and range."""
    default, low, high = local("ar")
    step = 0.5 if kind == "number" and isinstance(default, float) else 1.0
    return Spec(key, label, kind, default, low, high, step if kind == "number" else 0.0,
                local=local)


def saved_only(spec: Spec) -> Spec:
    """A setting that is never changed for one video alone."""
    return replace(spec, per_job=False)
