"""How well a listening model alone hears a clip of the bench: one request for the whole clip,
tarjim's own listening prompt, no vote, no second listener, no timing; the words it wrote
against the words said (words.py). For choosing between models on the first of the three.

    python hear.py <model> <passes> <clip> [clip ...]

Kept in runs/_hear/<model>/<clip>.json, each pass's lines too, so a model is asked once.
"""
import json
import os
import sys
from typing import Any

from paths import CLIPS, RUNS, prepare

prepare()
os.environ["TARJIM_GEMINI_MODEL"] = sys.argv[1]

from words import OK, plain, steps  # noqa: E402

from tarjim import media  # noqa: E402
from tarjim.gemini_client import GeminiClient  # noqa: E402
from tarjim.listen.gemini_listen import listen  # noqa: E402

Row = dict[str, Any]


def heard(clip: str, number: int) -> Row:
    truth = json.loads((CLIPS / clip / "truth.json").read_text(encoding="utf-8"))
    code = truth["language"].split("_")[0].replace("cmn", "zh")
    client = GeminiClient(listening=True)
    _language, lines = listen(media.audio_bytes(CLIPS / clip / "clip.wav", 0.0, None), client)
    said = [unit for sentence in truth["sentences"] for unit in plain(sentence["text"], code)]
    wrote = [unit for line in lines for unit in plain(line.text, code)]
    errors = sum(step.kind != OK for step in steps(said, wrote))
    return {"pass": number, "model": client.model_used, "errors": errors, "said": len(said),
            "lines": [[line.start, line.end, line.text] for line in lines]}


def main() -> None:
    model, passes, clips = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
    for clip in clips:
        kept = RUNS / "_hear" / model / f"{clip}.json"
        if not kept.exists():
            kept.parent.mkdir(parents=True, exist_ok=True)
            rows = [heard(clip, number) for number in range(passes)]
            kept.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        rows = json.loads(kept.read_text(encoding="utf-8"))
        shares = ", ".join(f"{100 * row['errors'] / row['said']:.1f}%" for row in rows)
        print(f"{clip:16} {model}: {shares} (by {sorted({row['model'] for row in rows})})",
              flush=True)


if __name__ == "__main__":
    main()
