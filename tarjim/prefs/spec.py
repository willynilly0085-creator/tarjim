"""One setting's description and the one gate every value passes (2026-11-09).

check(spec, raw) parses what the page, the chat or a hand-edited file gave, holds it to its
range or choices and returns the clean value, or a Refusal whose Arabic reason names a value
that would work. No other code parses a setting.
"""
import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

Value = bool | int | float | str
# A setting kept per target language (font, reading speed, line length): its default and range
# for one language code.
Local = Callable[[str], tuple[Value, float, float]]
NEAR = 1e-6
ON = {"on", "yes", "true", "1", "شغال", "شغّال", "نعم", "ايه"}
OFF = {"off", "no", "false", "0", "طافي", "لا"}
HEX = re.compile(r"#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})")
MOST_COLOURS = 6
FULL_HEX = 6
# A font name goes unescaped into the ASS Style line: a comma would shift every field after it.
FONT_NAME = re.compile(r"[^\W_][\w .'&+()-]{0,63}")


@dataclass(frozen=True)
class Spec:
    key: str
    label: str  # Arabic, as the page and every refusal call it
    kind: str  # switch, number, choice, colour, colours, font or folder
    default: Value
    low: float = 0.0
    high: float = 0.0
    step: float = 0.0  # 0: any value in the range
    choices: tuple[Value, ...] = ()
    tier: str = "basic"  # basic, or advanced (behind the page's closed disclosure)
    per_job: bool = True  # may be changed for one video without saving it
    local: Local | None = field(default=None, compare=False, repr=False)

    @property
    def group(self) -> str:
        return self.key.partition(".")[0]

    @property
    def per_language(self) -> bool:
        return self.local is not None

    def at(self, code: str) -> "Spec":
        """This setting for one target language: its own default and range."""
        if self.local is None:
            return self
        default, low, high = self.local(code)
        return replace(self, default=default, low=low, high=high)


@dataclass(frozen=True)
class Refusal:
    key: str
    reason: str  # Arabic, shown under the field or said in the chat
    works: Value | None = None  # a value that would be taken


def shown(value: Any) -> str:
    if isinstance(value, bool):
        return "شغّال" if value else "طافي"
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else f"{value:g}"
    return str(value).strip() or "(فاضي)"


def refuse(spec: Spec, why: str, works: Value | None = None) -> Refusal:
    tail = f" القيمة اللي تنفع: {shown(works)}." if works is not None else ""
    return Refusal(spec.key, f"«{spec.label}»: {why}.{tail}", works)


def typed(spec: Spec, value: float) -> Value:
    return round(value) if isinstance(spec.default, int) else round(value, 4)


def as_number(raw: Any) -> float | None:
    if isinstance(raw, bool):
        return None
    text = str(raw).strip().rstrip("%").replace("٫", ".").strip()
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def number(spec: Spec, raw: Any) -> Value | Refusal:
    value = as_number(raw)
    if value is None:
        return refuse(spec, "يبي رقم", spec.default)
    if not spec.low - NEAR <= value <= spec.high + NEAR:
        edge = typed(spec, min(max(value, spec.low), spec.high))
        return refuse(spec, f"لازم يكون من {shown(spec.low)} إلى {shown(spec.high)}", edge)
    if spec.step:
        on_step = spec.low + round((value - spec.low) / spec.step) * spec.step
        if abs(on_step - value) > NEAR:
            return refuse(spec, f"يمشي بخطوات {shown(spec.step)}", typed(spec, on_step))
        value = on_step
    if isinstance(spec.default, int) and not float(value).is_integer():
        return refuse(spec, "يبي رقم صحيح", typed(spec, value))
    return typed(spec, value)


def switch(spec: Spec, raw: Any) -> Value | Refusal:
    if isinstance(raw, bool):
        return raw
    said = str(raw).strip().lower()
    if said in ON or said in OFF:
        return said in ON
    return refuse(spec, "يا شغّال يا طافي", spec.default)


def same(choice: Value, raw: Any) -> bool:
    if str(choice).strip().lower() == str(raw).strip().lower():
        return True
    wanted, offered = as_number(raw), as_number(choice)
    return not isinstance(choice, str) and wanted is not None and offered == wanted


def choice(spec: Spec, raw: Any) -> Value | Refusal:
    found = next((c for c in spec.choices if same(c, raw)), None)
    if found is None:
        listed = "، ".join(shown(c) for c in spec.choices)
        return refuse(spec, f"اختر وحدة من: {listed}", spec.default)
    return found


def colour_of(raw: Any) -> str | None:
    found = HEX.fullmatch(str(raw).strip()) if isinstance(raw, str) else None
    if found is None:
        return None
    digits = found.group(1).upper()
    return "#" + (digits if len(digits) == FULL_HEX else "".join(d * 2 for d in digits))


def colour(spec: Spec, raw: Any) -> Value | Refusal:
    found = colour_of(raw)
    return found if found else refuse(spec, "اكتب اللون بالشكل ‎#RRGGBB", spec.default)


def colours(spec: Spec, raw: Any) -> Value | Refusal:
    parts = [p for p in re.split(r"[,،\s]+", str(raw).strip()) if p]
    found = [colour_of(p) for p in parts]
    if not 1 <= len(found) <= MOST_COLOURS or None in found:
        return refuse(spec, f"من لون إلى {MOST_COLOURS} ألوان ‎#RRGGBB بينها فواصل",
                      spec.default)
    return ",".join(c for c in found if c)


def font(spec: Spec, raw: Any) -> Value | Refusal:
    name = str(raw).strip() if isinstance(raw, str) else ""
    if FONT_NAME.fullmatch(name):
        return name
    return refuse(spec, "اسم خط بدون فواصل ولا أسطر، وأقل من 64 حرف", spec.default)


def check(spec: Spec, raw: Any) -> Value | Refusal:
    """The clean value, or why it cannot be taken. A missing value is refused, not guessed."""
    if raw is None or isinstance(raw, dict | list):
        return refuse(spec, "ما فيه قيمة", spec.default)
    if spec.kind == "folder":
        from tarjim.prefs.folders import folder

        return folder(spec, raw)
    return KINDS[spec.kind](spec, raw)


KINDS: dict[str, Callable[[Spec, Any], Value | Refusal]] = {
    "switch": switch, "number": number, "choice": choice, "colour": colour,
    "colours": colours, "font": font}
