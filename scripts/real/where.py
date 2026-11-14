"""Why a line of a run's kept hearing was or was not moved by the sound (listen/soundtime.py):
each line of the hearing the audio backs most, where the listener put it, how well it is heard
there, and where one free search of its request hears it.

    python where.py <label> <clip>
"""
import json
import sys
from functools import cache

import soundfile
from paths import CLIPS, RUNS, prepare

prepare()

from tarjim.asr.align import shared_aligner  # noqa: E402
from tarjim.listen.kept import load_heard  # noqa: E402
from tarjim.listen.recover import best_heard  # noqa: E402
from tarjim.listen.soundtime import Ears, moves  # noqa: E402


def main() -> None:
    label, clip = sys.argv[1:3]
    heard = load_heard(RUNS / label / clip / "cache" / "clip")
    assert heard is not None
    wav, _rate = soundfile.read(str(CLIPS / clip / "clip.wav"), dtype="float32")
    engine = shared_aligner()
    ears = Ears(engine.emitter.emissions(wav), cache(engine.tokens), heard.language)
    lines = sorted(best_heard(heard.utterances, heard.passes, []), key=lambda u: u.start)
    truth = json.loads((CLIPS / clip / "truth.json").read_text(encoding="utf-8"))
    print("said at:", [(s["start"], s["end"]) for s in truth["sentences"]])
    moved = False
    for line, found in zip(lines, ears.freely(lines), strict=True):
        moved = moves(ears, line, found, (True, moved))
        free = "nowhere" if found is None else f"{found[0]:.1f}-{found[1]:.1f} ({found[2]:.2f})"
        print(f"{line.request:7} put {line.start:6.1f}-{line.end:6.1f} heard there "
              f"{ears.here(line):.2f} | freely {free} | letters {len(ears.letters(line)):3} "
              f"| {'moves' if moved else 'stays'}")


if __name__ == "__main__":
    main()
