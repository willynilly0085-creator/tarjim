"""The files a release carries besides the Firefox add-on, made from its tag:

- install.sh, the one line for macOS and Linux
  (curl -fsSL .../releases/latest/download/install.sh | bash);
- tarjim-windows.zip, the folder with install.cmd that Windows users double-click.

GitHub counts the downloads of a release's files, and of nothing else that people fetch from the
repository (2026-11-22: the owner asked how many people downloaded tarjim, and the only counts
were clones, mostly GitHub's own test machines, and the add-on's file).

    python scripts/release_files.py vX.Y.Z <folder>
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def make(tag: str, folder: Path) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    script = subprocess.run(["git", "show", f"{tag}:scripts/unix/install.sh"], cwd=ROOT,
                            capture_output=True, check=True).stdout
    (folder / "install.sh").write_bytes(script.replace(b"\r\n", b"\n"))
    archive = folder / "tarjim-windows.zip"
    subprocess.run(["git", "archive", "--format=zip", "--prefix=tarjim/", "-o", str(archive),
                    tag], cwd=ROOT, check=True)
    return [folder / "install.sh", archive]


if __name__ == "__main__":
    for made in make(sys.argv[1], Path(sys.argv[2])):
        print(made)
