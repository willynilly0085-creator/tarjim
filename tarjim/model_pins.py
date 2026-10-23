"""Every model tarjim takes from Hugging Face, at one fixed commit that was looked at.

A commit names the exact files of a repository, so a model repository that is changed or taken
over later can never reach the person: tarjim downloads that commit only, and only the files it
needs (settings, tokenizer, chat template and safetensors weights; never code, and no pickled
weights except VoxCPM2's audiovae.pth, which VoxCPM loads with weights_only=True). Models are then
loaded from that folder on this computer, never by name, so loading never goes online. Checked
2026-10-15 and, for the Transformers-native Qwen3-ASR pair, 2026-10-23: no settings file at these
commits names remote code, a kernels repository or custom generation code, and the voice
separation weights name only demucs.htdemucs.HTDemucs. Where a pin names checksums (the SHA-256
Hugging Face publishes for each large file), a download counts only when every one matches, and
the model counts as here only when every one of those files is.
"""
import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Pin:
    revision: str
    files: tuple[str, ...]
    sha256: tuple[tuple[str, str], ...] = ()


SETTINGS_AND_WEIGHTS = ("*.json", "*.safetensors")
NATIVE = (*SETTINGS_AND_WEIGHTS, "chat_template.jinja")
CHUNK = 1 << 24
PINS = {
    "Qwen/Qwen3-ASR-1.7B-hf": Pin("bcd2b5b7f32b480ab5790554cfa8347f246a14f3", NATIVE, (
        ("model.safetensors", "2db53c7d81bd9b8cbc6a074e89be2c968a0d373fb4ee68bb1b1e14f7042dfee1"),
        ("tokenizer.json", "fe1fad59be22a41ee293363fcf95fdedbc7c93f3b49270b1d2e18bd1399a7a05"))),
    "Qwen/Qwen3-ForcedAligner-0.6B-hf": Pin("c07281df297b9905d24a508279258cccf987a064", NATIVE, (
        ("model.safetensors", "00568245ceca5af1991d28562a75fe1ddc9bfeb041c27fda66947ea05c47fb86"),
        ("tokenizer.json", "cadfb9cbd9ff8f4e309075ec6a71b063295ff796afb4b5dbc0fd2873fbb301f2"))),
    # The pair listening used before 2026-10-23, never downloaded again: kept only while the
    # Transformers-native pair above downloads (tarjim/listen_upgrade.py), then removed.
    "Qwen/Qwen3-ASR-1.7B": Pin("7278e1e70fe206f11671096ffdd38061171dd6e5",
                               (*SETTINGS_AND_WEIGHTS, "merges.txt")),
    "Qwen/Qwen3-ForcedAligner-0.6B": Pin("c7cbfc2048c462b0d63a45797104fc9db3ad62b7",
                                         (*SETTINGS_AND_WEIGHTS, "merges.txt")),
    "MahmoudAshraf/mms-300m-1130-forced-aligner": Pin("49402e9577b1158620820667c218cd494cc44486",
                                                      SETTINGS_AND_WEIGHTS),
    "openbmb/VoxCPM2": Pin("32279effe8c19989596f05d353d1447f51d9e915",
                           (*SETTINGS_AND_WEIGHTS, "audiovae.pth")),
    "adefossez/HTDemucs": Pin("cbc8a9b1a87023b7fd74e7b3412e6321c0eab003",
                              ("htdemucs.yaml", "*.safetensors")),
}


def folder(repo: str) -> Path:
    """The pinned copy on this computer. Raises when it is not there; never downloads."""
    from huggingface_hub import snapshot_download

    pin = PINS[repo]  # the files it takes: the hub counts any other file of the commit as missing
    where = Path(snapshot_download(repo, revision=pin.revision, allow_patterns=list(pin.files),
                                   local_files_only=True))
    missing = [name for name, _ in pin.sha256 if not (where / name).is_file()]
    if missing:
        raise FileNotFoundError(f"{repo} is not fully downloaded: {', '.join(missing)}")
    return where


def ready(repo: str) -> bool:
    try:
        folder(repo)
    except Exception:
        return False
    return True


def download(repo: str) -> Path:
    """Only while the caller has turned the hub online (tarjim.tools.online)."""
    from huggingface_hub import snapshot_download

    from tarjim.hub_fetch import fetch

    pin = PINS[repo]
    for name, expected in pin.sha256:
        fetch(repo, pin.revision, name, expected)
    return Path(snapshot_download(repo, revision=pin.revision, allow_patterns=list(pin.files)))


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


def check(path: Path, expected: str) -> None:
    """A file that differs from the published one is removed, so the next try fetches it again."""
    if sha256_of(path) == expected:
        return
    target = path.resolve()
    path.unlink(missing_ok=True)
    target.unlink(missing_ok=True)
    raise RuntimeError(f"{path.name} does not match the file tarjim checked; it was removed")


def cache_of(repo: str) -> Path:
    from huggingface_hub import constants

    return Path(constants.HF_HUB_CACHE) / f"models--{repo.replace('/', '--')}"


def snapshot(repo: str) -> Path:
    return cache_of(repo) / "snapshots" / PINS[repo].revision


def remove(repo: str) -> bool:
    """Delete the pinned copy from this computer: the whole model when no other version of it is
    in the shared cache, else only that version's folder. False when it was not there."""
    pinned = snapshot(repo)
    if not pinned.exists():
        return False
    others = [found for found in pinned.parent.iterdir() if found != pinned]
    shutil.rmtree(pinned if others else cache_of(repo))
    return True
