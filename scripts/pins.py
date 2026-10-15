"""Write tarjim/constraints.txt and tarjim/overrides.txt: the version of every library tarjim
installs, for Python 3.11 on Windows, macOS and Linux, except yt-dlp and the PyTorch family (see
tarjim/pins.py), and the libraries whose exact pin in another package is lifted (LIFTED below).

    python scripts/pins.py             keep what is pinned, add what is new
    python scripts/pins.py --upgrade   move everything to its newest version (the weekly check)
"""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tarjim.pins import FILE, OVERRIDES, PIN, canonical, floating  # noqa: E402

HEADER = ("# Tested versions of tarjim's libraries, written by scripts/pins.py; do not edit.\n"
          "# yt-dlp and the PyTorch family are left out on purpose (see tarjim/pins.py).\n")
LIFTED_HEADER = (
    "# Libraries whose exact pin in another package is replaced, written by scripts/pins.py; do\n"
    "# not edit. Each closes a known vulnerability and was tested with this release.\n")
# qwen-asr 0.0.6 requires accelerate==1.12.0 exactly; 1.15.0 closes PYSEC-2026-3804 and hears
# the same words at the same times (docs/decisions.md, 2026-10-15). transformers cannot be lifted
# the same way: every 5.x release stops qwen-asr 0.0.6 from loading.
LIFTED = {"accelerate": ">=1.15.0"}
# Only for working out the pins: people get the newest PyTorch for their card, so the libraries
# around it are pinned as they resolve beside a current one (Intel Macs stop at PyTorch 2.2).
TORCH_AS_INSTALLED = "torch>=2.6 ; platform_machine != 'x86_64' or sys_platform != 'darwin'\n"


def compile_pins(extra: list[str], folder: Path) -> None:
    lifted, torch = folder / "lifted.txt", folder / "torch.txt"
    lifted.write_text("".join(f"{name}{spec}\n" for name, spec in LIFTED.items()))
    torch.write_text(TORCH_AS_INSTALLED)
    subprocess.run(["uv", "pip", "compile", str(ROOT / "pyproject.toml"), "--extra", "dub",
                    "--universal", "--python-version", "3.11", "--no-annotate", "--no-header",
                    "--quiet", "--overrides", str(lifted), "-c", str(torch), "-o", str(FILE),
                    *extra], check=True)


def kept(line: str) -> bool:
    match = PIN.fullmatch(line.strip())
    return bool(match) and not floating(match[1] if match else "")


def lifted_lines(lines: list[str]) -> list[str]:
    names = {canonical(name) for name in LIFTED}
    return [line for line in lines
            if (match := PIN.fullmatch(line.strip())) and canonical(match[1]) in names]


def main(extra: list[str]) -> int:
    with tempfile.TemporaryDirectory() as folder:
        compile_pins(extra, Path(folder))
    lines = [line for line in FILE.read_text(encoding="utf-8").splitlines() if kept(line)]
    FILE.write_text(HEADER + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    OVERRIDES.write_text(LIFTED_HEADER + "\n".join(lifted_lines(lines)) + "\n", encoding="utf-8",
                         newline="\n")
    print(f"{len(lines)} libraries pinned in {FILE.relative_to(ROOT)}, "
          f"{len(LIFTED)} lifted in {OVERRIDES.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
