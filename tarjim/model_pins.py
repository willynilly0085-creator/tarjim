"""Every model tarjim takes from Hugging Face, at one fixed commit that was looked at.

A commit names the exact files of a repository, so a model repository that is changed or taken
over later can never reach the person: tarjim downloads that commit only, and only the files it
needs (settings, tokenizer and safetensors weights; never code, and no pickled weights except
VoxCPM2's audiovae.pth, which VoxCPM loads with weights_only=True). Models are then loaded from
that folder on this computer, never by name, so loading never goes online. Checked 2026-10-15:
no settings file at these commits names remote code, a kernels repository or custom generation
code, and the voice separation weights name only demucs.htdemucs.HTDemucs.
"""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Pin:
    revision: str
    files: tuple[str, ...]


SETTINGS_AND_WEIGHTS = ("*.json", "*.safetensors")
PINS = {
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

    return Path(snapshot_download(repo, revision=PINS[repo].revision, local_files_only=True))


def ready(repo: str) -> bool:
    try:
        folder(repo)
    except Exception:
        return False
    return True


def download(repo: str) -> Path:
    """Only while the caller has turned the hub online (tarjim.tools.online)."""
    from huggingface_hub import snapshot_download

    pin = PINS[repo]
    return Path(snapshot_download(repo, revision=pin.revision, allow_patterns=list(pin.files)))
