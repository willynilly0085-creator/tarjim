"""The settings page's routes (2026-11-09): read the table and values, save, reset, use or keep
a preset, list the fonts that write a language, and draw one real frame with values not saved
yet. Every value passes the one gate (tarjim/prefs) and is refused with an Arabic reason."""
import base64
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from tarjim.languages import LANGUAGES, language
from tarjim.prefs.spec import as_number
from tarjim.prefs.table import GROUPS, SPECS
from tarjim.server.jobs import Board
from tarjim.server.orders import first, local_file

Query = dict[str, list[str]]
Answer = tuple[int, dict[str, Any]]
NO_PRESET = "ما فيه مجموعة بهالاسم."


def target_of(raw: Any) -> str | None:
    code = str(raw or "ar")
    return code if code in LANGUAGES else None


def reset_what(data: dict[str, Any]) -> list[str] | None:
    """What a reset names: {"keys": [...]}, {"group": "look"}, {"what": ...} or {"all": true}."""
    if data.get("all") is True:
        return ["all"]
    keys = data.get("keys")
    if isinstance(keys, list):
        good = bool(keys) and all(isinstance(k, str) and k in SPECS for k in keys)
        return [str(k) for k in keys] if good else None
    what = data.get("group", data.get("what"))
    known = isinstance(what, str) and (what == "all" or what in GROUPS or what in SPECS)
    return [str(what)] if known else None


def saving(data: dict[str, Any]) -> Answer:
    from tarjim.prefs.edit import save_preset

    problem = save_preset(str(data["save_as"]))
    return (400, {"error": problem}) if problem else (200, {"saved": data["save_as"].strip()})


def renaming(data: dict[str, Any]) -> Answer:
    from tarjim.prefs.edit import rename_preset

    problem = rename_preset(str(data["rename"]), str(data.get("to", "")))
    return (400, {"error": problem}) if problem else (200, {"renamed": data["rename"]})


def deleting(data: dict[str, Any]) -> Answer:
    from tarjim.prefs.edit import delete_preset

    found = delete_preset(str(data["delete"]))
    return (200, {"deleted": data["delete"]}) if found else (404, {"error": NO_PRESET})


def using(data: dict[str, Any]) -> Answer:
    from tarjim.prefs.edit import use_preset

    used = use_preset(str(data["name"]))
    return (200, {"used": data["name"]}) if used else (404, {"error": NO_PRESET})


PRESET_ACTIONS: tuple[tuple[str, Callable[[dict[str, Any]], Answer]], ...] = (
    ("save_as", saving), ("rename", renaming), ("delete", deleting), ("name", using))


def preset_answer(data: dict[str, Any]) -> Answer:
    for field, act in PRESET_ACTIONS:
        if isinstance(data.get(field), str):
            return act(data)
    return 400, {"error": "اكتب اسم المجموعة."}


def active_preset() -> str:
    from tarjim.prefs.presets import active
    from tarjim.prefs.store import load

    kept = load()
    return active(kept.values, kept.presets)


class PrefsRoutes:
    board: ClassVar[Board]

    def reply(self, code: int, payload: Any) -> None:
        raise NotImplementedError

    def read_json(self) -> dict[str, Any]:
        raise NotImplementedError

    def kept(self, work: Callable[[], Answer]) -> None:
        """A save the preferences file being held by another program cannot make."""
        try:
            code, payload = work()
        except PermissionError:
            return self.reply(503, {"error": "busy"})
        self.reply(code, payload)

    def prefs_state(self, query: Query) -> None:
        from tarjim.prefs.view import state

        target, group = target_of(first(query, "lang")), first(query, "group")
        if target is None or (group and group not in GROUPS):
            return self.reply(400, {"error": "language" if target is None else "group"})
        self.reply(200, state(target, group))

    def prefs_fonts(self, query: Query) -> None:
        from tarjim.render.font_cover import covering

        target = target_of(first(query, "lang"))
        if target is None:
            return self.reply(400, {"error": "language"})
        found = covering(target)
        self.reply(200, {"language": target, "usual": language(target).font,
                         "fonts": found or [], "listed": found is not None})

    def prefs_save(self, _query: Query) -> None:
        from tarjim.prefs.view import save

        data = self.read_json()
        values, target = data.get("values"), target_of(data.get("language"))
        if not isinstance(values, dict) or not values or target is None:
            return self.reply(400, {"error": "values" if target else "language"})
        self.kept(lambda: (200, save(values, target)))

    def prefs_reset(self, _query: Query) -> None:
        from tarjim.prefs.edit import reset

        data = self.read_json()
        what, code = reset_what(data), str(data.get("language") or "")
        if what is None or (code and code not in LANGUAGES):
            return self.reply(400, {"error": "what" if what is None else "language"})
        self.kept(lambda: (200, {"reset": [k for w in what for k in reset(w, code)],
                                 "preset": active_preset()}))

    def prefs_preset(self, _query: Query) -> None:
        data = self.read_json()

        def answer() -> Answer:
            code, payload = preset_answer(data)
            return code, {**payload, "preset": active_preset()}

        self.kept(answer)

    def prefs_preview(self, _query: Query) -> None:
        from tarjim.prefs.view import trial

        data = self.read_json()
        values, target, shot = data.get("values", {}), target_of(data.get("language")), None
        if isinstance(values, dict) and target is not None:
            shot = self.shot_from(data)
        if shot is None or target is None:
            return self.reply(400, {"error": "preview"})
        prefs, refused = trial(values, target)
        self.drawn(prefs, shot, refused)

    def drawn(self, prefs: Any, shot: Any, refused: dict[str, str]) -> None:
        from tarjim.render.preview import still

        try:
            made = still(prefs, shot)
        except FileNotFoundError:
            return self.reply(503, {"error": "ffmpeg", "refused": refused})
        except (RuntimeError, OSError, ValueError) as error:
            return self.reply(422, {"error": "picture", "detail": str(error)[-200:],
                                    "refused": refused})
        image = "data:image/jpeg;base64," + base64.b64encode(made.image).decode("ascii")
        self.reply(200, {"image": image, "width": made.width, "height": made.height,
                         "font": made.font, "wraps": made.wraps, "refused": refused})

    def shot_from(self, data: dict[str, Any]) -> Any:
        """The frame asked for: the person's own video (a file's full path, or a job's), or
        tarjim's sample picture; None when the video named cannot be opened."""
        from tarjim.render.preview import Shot

        named = bool(data.get("path") or data.get("job"))
        video = self.video_of(data) if named else None
        if named and video is None:
            return None
        at = as_number(data.get("at", 0)) or 0.0
        return Shot(video, at, data.get("portrait") is True, str(data.get("text") or ""))

    def video_of(self, data: dict[str, Any]) -> Path | None:
        if data.get("path"):
            return local_file(str(data["path"]))
        task = self.board.get(str(data.get("job")))
        found = task.video if task else None
        return found if found is not None and found.is_file() else None
