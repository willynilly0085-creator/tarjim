"""Write tarjim/constraints.txt: the version of every library tarjim installs, for Python 3.11 on
Windows, macOS and Linux, except yt-dlp and the PyTorch family (see tarjim/pins.py).

    python scripts/pins.py             keep what is pinned, add what is new
    python scripts/pins.py --upgrade   move everything to its newest version (the weekly check)
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tarjim.pins import FILE, PIN, floating  # noqa: E402

HEADER = ("# Tested versions of tarjim's libraries, written by scripts/pins.py; do not edit.\n"
          "# yt-dlp and the PyTorch family are left out on purpose (see tarjim/pins.py).\n")


def compile_pins(extra: list[str]) -> None:
    subprocess.run(["uv", "pip", "compile", str(ROOT / "pyproject.toml"), "--extra", "dub",
                    "--universal", "--python-version", "3.11", "--no-annotate", "--no-header",
                    "--quiet", "-o", str(FILE), *extra], check=True)


def kept(line: str) -> bool:
    match = PIN.fullmatch(line.strip())
    return bool(match) and not floating(match[1] if match else "")


def main(extra: list[str]) -> int:
    compile_pins(extra)
    lines = [line for line in FILE.read_text(encoding="utf-8").splitlines() if kept(line)]
    FILE.write_text(HEADER + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(lines)} libraries pinned in {FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
