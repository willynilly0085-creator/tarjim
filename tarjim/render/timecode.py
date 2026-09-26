def split_ms(seconds: float) -> tuple[int, int, int, int]:
    total = max(0, round(seconds * 1000))
    hours, rest = divmod(total, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, millis = divmod(rest, 1000)
    return hours, minutes, secs, millis


def srt_time(seconds: float) -> str:
    h, m, s, ms = split_ms(seconds)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def ass_time(seconds: float) -> str:
    h, m, s, ms = split_ms(seconds)
    return f"{h}:{m:02d}:{s:02d}.{ms // 10:02d}"
