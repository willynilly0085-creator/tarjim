import threading
from pathlib import Path
from typing import Any

from tarjim import qualities
from tarjim.job import checkpoint, progress
from tarjim.media import tool

# The quality's name (tarjim_quality, set by tarjim) follows a space when there is one, so the
# same video in another quality is a file of its own.
NAME = "%(title).70s [%(id)s]%(tarjim_quality& {})s.%(ext)s"
MEDIA_SUFFIXES = (".mp4", ".mkv", ".webm", ".m4a", ".mp3")
LARGEST = 8 * 1024 ** 3
# What yt-dlp calls a link that stands for several videos. "noplaylist" only picks the video
# when a link names both a video and its list; a feed, a playlist, a channel or a page with
# several videos is still a list, and every entry would be downloaded.
LISTS = ("playlist", "multi_video")
A_LIST = "download refused: this link is a list of videos; send the link of one video"
TOO_BIG = "the download passed 8 GB and was stopped"
# Held while yt-dlp downloads, and while a newer yt-dlp replaces it (tarjim/downloader.py).
IN_USE = threading.Lock()


def is_url(text: str) -> bool:
    return text.strip().lower().startswith(("http://", "https://"))


def told(state: dict[str, Any]) -> None:
    """Pass the downloader's own count of bytes on to the job."""
    total = state.get("total_bytes") or state.get("total_bytes_estimate") or 0
    checkpoint()
    progress(int(state.get("downloaded_bytes") or 0), int(total))


class Budget:
    """The 8 GB is for the whole link, not for each piece: a video and its sound are two
    downloads. Some streams are handed to ffmpeg, which reports nothing while it runs, so ffmpeg
    is told to stop where what is left of the 8 GB runs out."""

    def __init__(self) -> None:
        self.pieces: dict[str, int] = {}
        self.ffmpeg = ["-fs", str(LARGEST)]

    def __call__(self, state: dict[str, Any]) -> None:
        self.pieces[str(state.get("filename"))] = int(state.get("downloaded_bytes") or 0)
        left = LARGEST - sum(self.pieces.values())
        if left < 0:
            raise RuntimeError(TOO_BIG)
        self.ffmpeg[1] = str(left)


def asking() -> dict[str, Any]:
    """Reading what a link is: one video or a list, live or not, and its qualities."""
    from yt_dlp.utils import match_filter_func

    return {"noplaylist": True, "quiet": True, "no_warnings": True,
            "match_filter": match_filter_func("!is_live"), "extract_flat": "in_playlist"}


def options(folder: Path, choice: Any = qualities.FALLBACK) -> dict[str, Any]:
    budget = Budget()
    return {**asking(), "format": choice, "outtmpl": str(folder / NAME),
            "merge_output_format": "mp4", "ffmpeg_location": tool("ffmpeg"),
            "progress_hooks": [budget, told], "max_filesize": LARGEST,
            "external_downloader_args": {"ffmpeg_o": budget.ffmpeg}}


def one_video(ydl: Any, url: str) -> dict[str, Any]:
    """What the link is, asked before anything is written: one video, or refused."""
    info = ydl.extract_info(url, download=False)
    if not info or info.get("_type") in LISTS:
        raise RuntimeError(A_LIST if info else f"download produced no media file for {url}")
    return dict(info)


def clear(folder: Path, name: str, before: set[Path]) -> None:
    """A download that failed or was cancelled leaves none of its pieces behind."""
    for path in set(folder.iterdir()) - before:
        if path.name.startswith(name) and path.is_file():
            path.unlink(missing_ok=True)


def look(url: str) -> dict[str, Any]:
    """The qualities this link offers, read without downloading anything. Not under IN_USE: a
    download holds it for as long as it runs, and reading must not wait behind one."""
    from yt_dlp import YoutubeDL

    with YoutubeDL({**asking(), "socket_timeout": qualities.ASK_SECONDS}) as ydl:
        return {**qualities.offer(ydl, one_video(ydl, url)), "limit": LARGEST}


def download(url: str, folder: Path, quality: str = "") -> Path:
    with IN_USE:
        return download_now(url, folder, quality)


def download_now(url: str, folder: Path, quality: str = "") -> Path:
    """quality: a number of lines such as "720", "audio", or nothing for 1080p or the nearest
    below it. The link is read once, and exactly the picked quality is downloaded."""
    from yt_dlp import YoutubeDL

    folder.mkdir(parents=True, exist_ok=True)
    before = set(folder.iterdir())
    choice = qualities.Choice(quality)
    with YoutubeDL(options(folder, choice)) as ydl:
        choice.ydl = ydl
        info = {**one_video(ydl, url), "tarjim_quality": choice.named}
        path = Path(ydl.prepare_filename(info))
        try:
            ydl.process_ie_result(info, download=True)
            return media(path, url)
        except BaseException:
            clear(folder, path.stem, before)
            raise


def media(path: Path, url: str) -> Path:
    """The file the link gave, checked once more against the limit: what ffmpeg wrote was never
    counted while it ran."""
    found = [path.with_suffix(s) for s in MEDIA_SUFFIXES if path.with_suffix(s).is_file()]
    if not found and not path.is_file():
        raise FileNotFoundError(f"download produced no media file for {url}")
    video = found[0] if found else path
    if video.stat().st_size > LARGEST:
        raise RuntimeError(TOO_BIG)
    return video


def resolve(source: str, folder: Path, quality: str = "") -> Path:
    return download(source, folder, quality) if is_url(source) else Path(source)
