from pathlib import Path
from typing import Any

from tarjim.job import progress
from tarjim.media import tool

FORMAT = "bv*[ext=mp4][height<=1080]+ba[ext=m4a]/b[ext=mp4]/b"
NAME = "%(title).70s [%(id)s].%(ext)s"
MEDIA_SUFFIXES = (".mp4", ".mkv", ".webm", ".m4a", ".mp3")


def is_url(text: str) -> bool:
    return text.strip().lower().startswith(("http://", "https://"))


def told(state: dict[str, Any]) -> None:
    """Pass the downloader's own count of bytes on to the job."""
    total = state.get("total_bytes") or state.get("total_bytes_estimate") or 0
    progress(int(state.get("downloaded_bytes") or 0), int(total))


def download(url: str, folder: Path) -> Path:
    from yt_dlp import YoutubeDL

    folder.mkdir(parents=True, exist_ok=True)
    options = {"format": FORMAT, "outtmpl": str(folder / NAME), "merge_output_format": "mp4",
               "ffmpeg_location": tool("ffmpeg"), "noplaylist": True, "quiet": True,
               "no_warnings": True, "progress_hooks": [told]}
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))
    found = [path.with_suffix(s) for s in MEDIA_SUFFIXES if path.with_suffix(s).is_file()]
    if not found and not path.is_file():
        raise FileNotFoundError(f"download produced no media file for {url}")
    return found[0] if found else path


def resolve(source: str, folder: Path) -> Path:
    return download(source, folder) if is_url(source) else Path(source)
