"""The files a release carries besides the Firefox add-on, made from its tag:

- install.sh, the one line for macOS and Linux
  (curl -fsSL .../releases/latest/download/install.sh | bash);
- tarjim-windows.zip, the folder with install.cmd that Windows users double-click;
- tarjim-update.zip, tarjim-release.json and tarjim-release.sig, what engines update from: the
  same code, its description, and the description's signature with the key in the owner's
  Keychain (scripts/release_key.py; tarjim/signed_release.py says what an engine checks). An
  engine refuses a release without them, so every file in the folder goes up with the release.

GitHub counts the downloads of a release's files, and of nothing else that people fetch from the
repository (2026-11-22: the owner asked how many people downloaded tarjim, and the only counts
were clones, mostly GitHub's own test machines, and the add-on's file).

    python scripts/release_files.py vX.Y.Z <folder>
"""
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tarjim import signed_release  # noqa: E402


def git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def signed_update(tag: str, code: Path, sign: Callable[[bytes], bytes]) -> list[Path]:
    """The update's zip, its description and the signature, refused unless a key engines
    already carry checks it."""
    archive = shutil.copyfile(code, code.with_name(signed_release.ARCHIVE))
    commit = git("rev-parse", "--verify", f"{tag}^{{commit}}").decode().strip()
    manifest = signed_release.describe(tag, commit, archive.read_bytes())
    signature = sign(signed_release.message(manifest))
    if not signed_release.verify(manifest, signature):
        raise SystemExit("the release key is not one tarjim/signed_release.py carries")
    described = archive.with_name(signed_release.MANIFEST)
    described.write_bytes(manifest)
    signed = archive.with_name(signed_release.SIGNATURE)
    signed.write_bytes(signature)
    return [archive, described, signed]


def make(tag: str, folder: Path, sign: Callable[[bytes], bytes]) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    script = git("show", f"{tag}:scripts/unix/install.sh")
    (folder / "install.sh").write_bytes(script.replace(b"\r\n", b"\n"))
    archive = folder / "tarjim-windows.zip"
    git("archive", "--format=zip", "--prefix=tarjim/", "-o", str(archive), tag)
    return [folder / "install.sh", archive, *signed_update(tag, archive, sign)]


if __name__ == "__main__":
    import release_key

    for made in make(sys.argv[1], Path(sys.argv[2]), release_key.sign):
        print(made)
