# tarjim

Arabic subtitles for any video with professional timing. See `README.md` and `docs/decisions.md`.

- Gates before claiming done: `pytest -q`, `ruff check tarjim tests`, `mypy tarjim` (strict).
- Limits: files 200 lines, functions 20 lines, complexity 6, 4 args.
- Timing is decided locally (aligner + rules); the LLM only fills fixed cues.
- Never commit keys, models, samples or `.venv`.
- Local test run needs `HF_HOME=.models`, `TARJIM_FFMPEG`, `TARJIM_FFPROBE`, `GEMINI_API_KEY`.
