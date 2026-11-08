"""The person's settings on disk: HOME/preferences.json (2026-11-09).

{"version": 1, "values": {key: value | {language: value}}, "presets": {name: values}}. Only
what differs from a default is kept, so a reset deletes the key and a default improved in a
release reaches whoever never changed it. The file is written whole, under config's own lock.
config.json keeps setup (engines, models, keys); the settings it used to hold are copied over
once, the first time this file is missing, and its old names still work from the environment
(TARJIM_VIDEO_MARK and the rest) for tests and scripts.
"""
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tarjim import config
from tarjim.prefs.model import Prefs, resolve
from tarjim.prefs.spec import Refusal, check
from tarjim.prefs.table import SPECS

FILE = "preferences.json"
VERSION = 1
# The settings config.json held before this file: their new key and their old name.
MIGRATED = {"look.mark": "video_mark", "listen.chunk_seconds": "listen_chunk_seconds",
            "listen.gap_seconds": "coverage_gap_seconds", "output.folder": "downloads"}
SAID: set[str] = set()


@dataclass
class Kept:
    values: dict[str, Any] = field(default_factory=dict)
    presets: dict[str, dict[str, Any]] = field(default_factory=dict)


def path() -> Path:
    return Path(config.HOME) / FILE


def note(line: str) -> None:
    """Into server.log, once a run: the same file is read for every job."""
    if line not in SAID:
        SAID.add(line)
        print(line, flush=True)


def kept_from(data: Any) -> Kept:
    if not isinstance(data, dict):
        raise ValueError("not an object")
    values, presets = data.get("values", {}), data.get("presets", {})
    own = {str(k): v for k, v in presets.items() if isinstance(v, dict)} if isinstance(
        presets, dict) else {}
    return Kept(dict(values) if isinstance(values, dict) else {}, own)


def migrated() -> Kept:
    """The settings an older tarjim kept in config.json, each through the gate."""
    old, values = config.settings(), {}
    for key, name in MIGRATED.items():
        if not old.get(name):
            continue
        found = check(SPECS[key], old[name])
        if isinstance(found, Refusal):
            note(f"preferences: config.json {name} = {old[name]!r} was not taken")
        elif found != SPECS[key].default:
            values[key] = found
    return Kept(values)


def load() -> Kept:
    """What was saved. A hand-edited file that cannot be read leaves every default in place."""
    try:
        return kept_from(json.loads(path().read_text(encoding="utf-8")))
    except FileNotFoundError:
        return migrated()
    except (OSError, ValueError) as error:
        note(f"preferences: {path()} could not be read ({error}); the defaults are used")
        return Kept()


def for_saving() -> Kept:
    """What a save builds on. A busy file stops the save; a damaged one is set aside."""
    for _ in range(config.TRIES):
        try:
            return kept_from(json.loads(path().read_text(encoding="utf-8")))
        except FileNotFoundError:
            return migrated()
        except ValueError:
            os.replace(path(), path().with_name("preferences.broken.json"))
            note("preferences: a damaged preferences.json was set aside")
            return Kept()
        except OSError:
            time.sleep(config.PAUSE)
    raise PermissionError("the preferences file is in use by another program")


def write(kept: Kept) -> None:
    config.write_json(path(), {"version": VERSION, "values": kept.values,
                               "presets": kept.presets})


def from_environment() -> dict[str, Any]:
    """The old names set in the environment, each through the gate: one that cannot be taken
    leaves the saved value in place."""
    found = {}
    for key, name in MIGRATED.items():
        raw = os.environ.get(f"TARJIM_{name.upper()}", "")
        value = check(SPECS[key], raw) if raw else None
        if isinstance(value, Refusal):
            note(f"preferences: TARJIM_{name.upper()} = {raw!r} was not taken")
        elif value is not None:
            found[key] = value
    return found


def current(target: str = "ar", tweaks: dict[str, Any] | None = None) -> Prefs:
    """The settings a job made now runs with; each note goes to server.log once."""
    prefs = resolve({**load().values, **from_environment()}, tweaks or {}, target)
    for line in prefs.notes:
        note(line)
    return prefs
