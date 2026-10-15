from pathlib import Path
from typing import Any

from tarjim.job import checkpoint, progress
from tarjim.media import tool

FORMAT = "bv*[ext=mp4][height<=1080]+ba[ext=m4a]/b[ext=mp4]/b"
NAME = "%(title).70s [%(id)s].%(ext)s"
MEDIA_SUFFIXES = (".mp4", ".mkv", ".webm", ".m4a", ".mp3")
LARGEST = 8 * 1024 ** 3
# What yt-dlp calls a link that stands for several videos. "noplaylist" only picks the video
# when a link names both a video and its list; a feed, a playlist, a channel or a page with
# several videos is still a list, and every entry would be downloaded.
LISTS = ("playlist", "multi_video")
A_LIST = "download refused: this link is a list of videos; send the link of one video"
TOO_BIG = "the download passed 8 GB and was stopped"


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


def options(folder: Path) -> dict[str, Any]:
    from yt_dlp.utils import match_filter_func

    budget = Budget()
    return {"format": FORMAT, "outtmpl": str(folder / NAME), "merge_output_format": "mp4",
            "ffmpeg_location": tool("ffmpeg"), "noplaylist": True, "quiet": True,
            "no_warnings": True, "progress_hooks": [budget, told], "max_filesize": LARGEST,
            "external_downloader_args": {"ffmpeg_o": budget.ffmpeg},
            "match_filter": match_filter_func("!is_live"), "extract_flat": "in_playlist"}


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


def download(url: str, folder: Path) -> Path:
    from yt_dlp import YoutubeDL

    folder.mkdir(parents=True, exist_ok=True)
    before = set(folder.iterdir())
    with YoutubeDL(options(folder)) as ydl:
        info = one_video(ydl, url)
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


def resolve(source: str, folder: Path) -> Path:
    return download(source, folder) if is_url(source) else Path(source)
