"""The voice of a clip without what is under it, made with the separation tarjim already has
for dubbing (dub/separate.py), kept beside the clip as voices.wav: to measure whether a
listener hears a clip better from its voice alone (hear.py with HEAR_SOUND=voices).

    python voices.py <clip> [clip ...]
"""
import sys
import time

import soundfile
from paths import CLIPS, prepare

prepare()

from tarjim.dub.audio import RATE  # noqa: E402
from tarjim.dub.separate import separate  # noqa: E402


def main() -> None:
    for clip in sys.argv[1:]:
        started = time.monotonic()
        stems = separate(CLIPS / clip / "clip.wav")
        soundfile.write(str(CLIPS / clip / "voices.wav"), stems.voices, RATE, subtype="PCM_16")
        print(f"{clip}: separated {stems.separated}, {len(stems.voices) / RATE:.0f} s of sound in "
              f"{time.monotonic() - started:.0f} s", flush=True)


if __name__ == "__main__":
    main()
