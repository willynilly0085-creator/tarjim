from pathlib import Path

from tarjim.media import run, tool

ENCODERS = [
    ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "21", "-b:v", "0"],
    ["-c:v", "libx264", "-crf", "19", "-preset", "medium"],
]


def filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def burn(video: Path, ass: Path, target: Path, fonts_dir: Path | None = None) -> Path:
    fonts = f":fontsdir='{filter_path(fonts_dir)}'" if fonts_dir else ""
    vf = f"ass='{filter_path(ass)}'{fonts}"
    base = [tool("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error", "-i", str(video),
            "-vf", vf, "-c:a", "copy", "-movflags", "+faststart"]
    errors = []
    for encoder in ENCODERS:
        result = run([*base, *encoder, str(target)])
        if result.returncode == 0 and target.exists() and target.stat().st_size > 0:
            return target
        errors.append(result.stderr.strip()[-200:])
    raise RuntimeError("burn failed: " + " | ".join(errors))
