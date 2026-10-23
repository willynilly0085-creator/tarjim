"""H.264 encoders tried in turn, so every computer can write video.

The graphics card's own encoder first (NVIDIA, Intel, AMD), then x264 when the ffmpeg has it,
then OpenH264 and Windows' Media Foundation. tarjim's own ffmpeg is an LGPL build without x264,
so a computer with no NVIDIA card used to fail at the burn and at the phone copy; OpenH264 is
in that build on every computer. An encoder the computer lacks fails at once and the next is
tried.
"""
FALLBACK_KBPS = 4000


def for_quality(kbps: int) -> list[list[str]]:
    """Burning subtitles: aim at a quality; the last two have no quality mode, so a rate."""
    return [["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "21", "-b:v", "0"],
            ["-c:v", "h264_qsv", "-global_quality", "21"],
            ["-c:v", "h264_amf", "-rc", "qvbr", "-qvbr_quality_level", "21"],
            ["-c:v", "libx264", "-crf", "19", "-preset", "medium"],
            *for_rate(kbps or FALLBACK_KBPS)[-2:]]


def for_rate(kbps: int) -> list[list[str]]:
    """A set bitrate (the phone copy, and the last resort of a burn)."""
    rate = ["-b:v", f"{kbps}k"]
    return [["-c:v", "h264_nvenc", *rate], ["-c:v", "h264_qsv", *rate],
            ["-c:v", "h264_amf", *rate], ["-c:v", "libx264", "-preset", "veryfast", *rate],
            ["-c:v", "libopenh264", *rate], ["-c:v", "h264_mf", "-pix_fmt", "nv12", *rate]]
