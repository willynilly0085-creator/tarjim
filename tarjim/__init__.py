import os

__version__ = "1.1.28"

# On a Mac with an Apple chip, an operation Metal does not have runs on the processor instead of
# failing the model (tarjim/device.py). PyTorch reads this once, when it loads, so it is set here.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
