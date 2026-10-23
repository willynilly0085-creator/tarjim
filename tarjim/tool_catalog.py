"""What tarjim can download or set up: each tool, where it comes from, its size and licence."""
from dataclasses import dataclass

VOICE_REPO = "openbmb/VoxCPM2"


@dataclass(frozen=True)
class License:
    name: str
    url: str
    commercial: bool
    consent: bool = False


@dataclass(frozen=True)
class Tool:
    id: str
    sources: tuple[str, ...]
    size_gb: float
    required: bool
    kind: str
    license: License


MMS = License("CC-BY-NC-4.0", "https://huggingface.co/MahmoudAshraf/mms-300m-1130-forced-aligner",
              commercial=False)
QWEN = License("Apache-2.0", "https://huggingface.co/Qwen/Qwen3-ASR-1.7B-hf", commercial=True)
APACHE = License("Apache-2.0", "https://huggingface.co/openbmb/VoxCPM2", commercial=True)
AYA = License("CC-BY-NC-4.0", "https://ollama.com/library/aya-expanse", commercial=False)
LGPL = License("LGPL-2.1", "https://ffmpeg.org/legal.html", commercial=True)
TOOLS = [
    Tool("ffmpeg", ("BtbN/FFmpeg-Builds",), 0.08, True, "ffmpeg", LGPL),
    Tool("timing", ("MahmoudAshraf/mms-300m-1130-forced-aligner",), 1.2, True, "hub", MMS),
    Tool("accuracy", ("Qwen/Qwen3-ASR-1.7B-hf", "Qwen/Qwen3-ForcedAligner-0.6B-hf"), 5.9, False,
         "hub", QWEN),
    Tool("dubbing", (VOICE_REPO,), 4.7, False, "voice", APACHE),
    Tool("local_translation", ("aya-expanse:8b",), 5.1, False, "ollama", AYA),
]
BY_ID = {tool.id: tool for tool in TOOLS}
