# How Anthropic's OSS Scanner builds tarjim (https://github.com/anthropics/oss-scanner).
# The build context is the repository root. The network is available here and gone afterwards,
# so everything the tests need is installed in this file. No model weights are downloaded: the
# tests do not need them, and neither does reading the code that faces untrusted input.
FROM python:3.11-bookworm
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10 \
    HF_HUB_OFFLINE=1 \
    TARJIM_FFMPEG=/usr/bin/ffmpeg \
    TARJIM_FFPROBE=/usr/bin/ffprobe
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates git ffmpeg curl \
    && rm -rf /var/lib/apt/lists/*

# scanner contract: the checkout lives inside the image, at /src
COPY . /src
WORKDIR /src

# The same install as CI (.github/workflows/ci.yml): the processor build of PyTorch, then tarjim
# with its development tools.
RUN pip install --extra-index-url https://download.pytorch.org/whl/cpu -e ".[dev]"

# The gates CI runs. A failure is reported but does not stop the image from being built.
RUN ruff check tarjim tests || echo "WARNING: ruff reported problems"
RUN mypy tarjim || echo "WARNING: mypy reported problems"
RUN pytest -q || echo "WARNING: pytest reported failures"
