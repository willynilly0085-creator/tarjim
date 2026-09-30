"""Pick the file the person asked for and make a copy that suits a phone: at most 720p and a
bitrate a phone screen needs, so it uploads quickly and fits Telegram's 50 MB limit for bots. A
video too long to fit at a watchable quality is replaced by the subtitle file, and the full video
stays on the computer."""
from pathlib import Path

from tarjim.phone.telegram import SEND_LIMIT

AIM = 45 * 1024 * 1024
DIRECT = 20 * 1024 * 1024
AUDIO_KBPS = 96
PHONE_KBPS = 1800
LOWEST_VIDEO_KBPS = 250


def chosen_output(outputs: list[Path], mode: str) -> Path | None:
    videos = [p for p in outputs if p.suffix == ".mp4"]
    if mode == "srt":
        return next((p for p in outputs if p.suffix == ".srt"), None)
    if mode.startswith("dub-"):
        return next((p for p in videos if ".dub." in p.name), videos[0] if videos else None)
    return next((p for p in videos if ".dub." not in p.name), None)


def video_kbps(seconds: float) -> int:
    return int(AIM * 8 / 1000 / max(seconds, 1.0)) - AUDIO_KBPS


def phone_copy(video: Path) -> Path | None:
    """The video itself when it is small, otherwise a phone copy; None when none can fit."""
    from tarjim.media import probe, run, tool

    if video.stat().st_size <= DIRECT:
        return video
    rate = min(PHONE_KBPS, video_kbps(probe(video).duration))
    if rate < LOWEST_VIDEO_KBPS:
        return None
    smaller = video.with_name(f"{video.stem}.phone.mp4")
    run([tool("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error", "-i", str(video),
         "-vf", "scale='min(1280,iw)':-2", "-c:v", "libx264", "-preset", "veryfast",
         "-b:v", f"{rate}k", "-maxrate", f"{rate}k", "-bufsize", f"{2 * rate}k",
         "-c:a", "aac", "-b:a", f"{AUDIO_KBPS}k", "-movflags", "+faststart", str(smaller)])
    return smaller if smaller.is_file() and smaller.stat().st_size <= SEND_LIMIT else None
