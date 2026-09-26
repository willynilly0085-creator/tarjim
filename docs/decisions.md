# Decisions

- 2026-09-26 — ASR is `Qwen3-ASR-1.7B` + `Qwen3-ForcedAligner-0.6B` instead of Whisper large-v3. Whisper is no longer the most accurate open model in 2026, and its word timestamps drift by roughly half a second, which is what merged several speakers into one subtitle.
- 2026-09-26 — Timing never comes from the LLM. Words are force-aligned locally; the translator only fills fixed cues and cannot merge or split them.
- 2026-09-26 — Speaker changes are detected from pauses, sentence ends and video shot changes before diarization is added, because edited montages change speaker on every cut with no pause.
- 2026-09-26 — Heavy engines (`qwen_asr`, `google.genai`) are imported inside the functions that use them, so tests, rendering and segmentation run without the models installed. Ruff rule PLC0415 is disabled for this reason.
- 2026-09-26 — Breaks: shot cut, sentence end, or a pause of 2.5 s inside an unfinished sentence. Shorter pauses keep a sentence together ("Longer than … that.").
- 2026-09-26 — Pieces shorter than 0.9 s are joined with a neighbour. Across a shot cut they become a two-line dialogue subtitle with dashes; otherwise the same speaker continues. Gemini hears the audio and collapses a dialogue back to one line when both parts are the same person.
- 2026-09-26 — `gemini-2.5-flash` was withdrawn for new keys; the translator falls back through the 3.x Flash models on 503 errors.
- 2026-09-26 — Subtitles are rendered as ASS sized from the real video resolution (font 5.8% of the short side, portrait videos get a higher bottom margin) instead of a fixed SRT style.
