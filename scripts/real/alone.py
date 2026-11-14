"""Whether a listener hears a sentence better when it is given that sentence's sound alone than
inside the whole clip: each sentence of a clip cut out by its true times (EDGE either side) and
heard on its own, tarjim's listening prompt, against the same model's hearing of the whole clip
(hear.py). For deciding whether hearing a doubted line again by itself is worth building.

    python alone.py <model> <passes> <clip> [clip ...]

Kept in runs/_alone/<model>/<clip>.json.
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

EDGE = 0.4
Row = dict[str, Any]


def heard(clip: str, sentence: Row, code: str) -> Row:
    sound = media.audio_bytes(CLIPS / clip / "clip.wav", max(0.0, sentence["start"] - EDGE),
                              sentence["end"] + EDGE)
    _language, lines = listen(sound, GeminiClient(listening=True))
    said, wrote = plain(sentence["text"], code), plain(" ".join(u.text for u in lines), code)
    return {"errors": sum(step.kind != OK for step in steps(said, wrote)), "said": len(said),
            "wrote": " ".join(u.text for u in lines)}


def main() -> None:
    model, passes, clips = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
    for clip in clips:
        kept = RUNS / "_alone" / model / f"{clip}.json"
        truth = json.loads((CLIPS / clip / "truth.json").read_text(encoding="utf-8"))
        code = truth["language"].split("_")[0].replace("cmn", "zh")
        if not kept.exists():
            kept.parent.mkdir(parents=True, exist_ok=True)
            rows = [[heard(clip, sentence, code) for sentence in truth["sentences"]]
                    for _ in range(passes)]
            kept.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        rows = json.loads(kept.read_text(encoding="utf-8"))
        wrong = [sum(r["errors"] for r in one) / sum(r["said"] for r in one) for one in rows]
        shares = ", ".join(f"{100 * share:.1f}%" for share in wrong)
        each = [sorted(one[k]["errors"] for one in rows) for k in range(len(rows[0]))]
        print(f"{clip:14} each sentence alone: {shares} | errors by sentence {each}", flush=True)


if __name__ == "__main__":
    main()
