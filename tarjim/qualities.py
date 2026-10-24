"""The qualities a link really offers, read from yt-dlp before anything downloads, and the one
the person picked turned into what yt-dlp downloads.

A quality is named by the picture's shorter side, the way sites name it: a portrait video 1080
wide and 1920 high is "1080p". 1080p, or the nearest below it, is chosen unless the person picks
another, and nothing is remembered from one link to the next (the owner, 2026-10-24). "audio"
is the sound alone, offered when the site has it apart from the picture.

HDR is left out where an SDR picture of the same height exists: burning writes 8-bit H.264,
and an HDR picture written that way without tone mapping comes out grey and washed out.
"""
from typing import Any

AUDIO = "audio"
DEFAULT = 1080
AUDIO_SPEC = "ba[ext=m4a]/ba"
# A site that names no heights (a plain file, most feeds): what tarjim always downloaded.
FALLBACK = "bv*[ext=mp4][height<=1080]+ba[ext=m4a]/b[ext=mp4]/b"
ASK_SECONDS = 15
DIGITS = 5  # the most a quality's number may have


def spec(height: int) -> str:
    sized = f"[height={height}]"
    sdr = f"{sized}[dynamic_range=?SDR]"
    return f"bv*{sdr}+ba[ext=m4a]/bv*{sdr}+ba/bv*{sized}+ba/b{sized}"


def has_picture(found: dict[str, Any]) -> bool:
    return found.get("vcodec") != "none" and bool(found.get("height"))


def has_sound_alone(formats: list[dict[str, Any]]) -> bool:
    return any(f.get("vcodec") == "none" and f.get("acodec") not in (None, "none")
               for f in formats)


def side(found: dict[str, Any]) -> int:
    height, width = int(found["height"]), int(found.get("width") or 0)
    return min(height, width) if width else height


def heights(formats: list[dict[str, Any]]) -> dict[int, int]:
    """Each quality's name (the shorter side) with the height yt-dlp selects it by."""
    named: dict[int, int] = {}
    for found in filter(has_picture, formats):
        named[side(found)] = max(named.get(side(found), 0), int(found["height"]))
    return named


def nearest(names: list[int], wanted: int) -> int:
    below = [name for name in names if name <= wanted]
    return max(below) if below else min(names)


def wanted_name(quality: str) -> int:
    return int(quality) if quality.isdigit() and len(quality) <= DIGITS else DEFAULT


def pick(formats: list[dict[str, Any]], quality: str) -> tuple[str, str]:
    """What yt-dlp downloads for this choice, and the words added to the file's name."""
    if quality == AUDIO and has_sound_alone(formats):
        return AUDIO_SPEC, AUDIO
    named = heights(formats)
    if not named:
        return FALLBACK, ""
    name = nearest(list(named), wanted_name(quality))
    return spec(named[name]), f"{name}p"


def clean(quality: object) -> str:
    """What an order may carry: a number of lines, "audio", or nothing for the default."""
    text = str(quality or "").strip().lower()
    return text if text == AUDIO or (text.isdigit() and len(text) <= DIGITS) else ""


def piece_size(found: dict[str, Any], seconds: float) -> int:
    stated = found.get("filesize") or found.get("filesize_approx")
    return int(stated or float(found.get("tbr") or 0) * 125 * seconds)


def size(ydl: Any, info: dict[str, Any], wanted: str) -> int:
    """The bytes yt-dlp itself would download for this choice; 0 when the site gives no hint."""
    formats = list(info.get("formats") or [])
    whole = any("none" not in (f.get("acodec"), f.get("vcodec")) for f in formats)
    partial = (all(f.get("vcodec") == "none" for f in formats)
               or all(f.get("acodec") == "none" for f in formats))
    ctx = {"formats": formats, "has_merged_format": whole, "incomplete_formats": partial}
    chosen = next(iter(ydl.build_format_selector(wanted)(ctx)), None)
    if chosen is None:
        return 0
    seconds = float(info.get("duration") or 0)
    pieces = chosen.get("requested_formats") or [chosen]
    return sum(piece_size(piece, seconds) for piece in pieces)


def offer(ydl: Any, info: dict[str, Any]) -> dict[str, Any]:
    """Every quality the link has, largest first, each with its approximate size."""
    formats = list(info.get("formats") or [])
    named = heights(formats)
    choices = [{"id": str(name), "label": f"{name}p", "size": size(ydl, info, spec(named[name]))}
               for name in sorted(named, reverse=True)]
    sound = {"size": size(ydl, info, AUDIO_SPEC)} if has_sound_alone(formats) else None
    default = str(nearest(list(named), DEFAULT)) if named else ""
    return {"title": str(info.get("title") or ""), "choices": choices, "audio": sound,
            "default": default}


class Choice:
    """yt-dlp's format selector for the picked quality, decided from the formats the link has.
    yt-dlp calls it when it reads the link and again when it downloads, so both agree; the
    quality's name is kept for the file's name."""

    def __init__(self, quality: str) -> None:
        self.quality, self.named = quality, ""
        self.ydl: Any = None

    def __call__(self, ctx: dict[str, Any]) -> Any:
        wanted, self.named = pick(list(ctx.get("formats") or []), self.quality)
        if self.ydl is None:
            raise RuntimeError("the downloader was not given its yt-dlp")
        return self.ydl.build_format_selector(wanted)(ctx)
