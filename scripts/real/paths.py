"""Where the real-speech bench keeps its work, and the environment tarjim runs in for it: a home
of its own (never the owner's settings or kept work), the tools and the models of this clone.

Nothing here is committed: the material is other people's recordings (FLEURS, CC-BY-4.0)."""
import os
import sys
from pathlib import Path

REAL = Path(os.environ.get("TARJIM_REAL", r"C:\Users\PC\Desktop\tarjim-files\tarjim-real"))
REPO = Path(__file__).resolve().parents[2]
TOOLS = Path(r"C:\Users\PC\.tarjim\tools\ffmpeg\368ccdd16812dd8b"
             r"\ffmpeg-n8.1-latest-win64-lgpl-shared-8.1\bin")
MATERIAL, CLIPS, RUNS = REAL / "material", REAL / "clips", REAL / "runs"
RATE = 16000


def prepare() -> None:
    """Before tarjim is imported: its home, tools and models, and this clone's code first."""
    clone = REPO.parents[2] if ".claude" in REPO.parts else REPO  # a worktree's models
    usual = {"TARJIM_FFMPEG": str(TOOLS / "ffmpeg.exe"),
             "TARJIM_FFPROBE": str(TOOLS / "ffprobe.exe"), "HF_HOME": str(clone / ".models")}
    for key, value in usual.items():
        os.environ.setdefault(key, value)
    os.environ["TARJIM_HOME"] = str(REAL / "home")  # never the owner's settings
    os.environ.setdefault("TARJIM_LISTEN_PROVIDER", "gemini")
    os.environ.setdefault("TARJIM_TRANSLATE_PROVIDER", "gemini")
    sys.path[:0] = [str(Path(__file__).resolve().parent), str(REPO)]
