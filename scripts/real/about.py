"""What a link would say of some clips of the bench, written beside them the way a download
leaves it (listen/known.py), to measure what telling the listener does: a title and a
description as people write them, naming people and places that are said in the clip and others
that are not. A clip with only names that are not said shows whether any gets written anyway.

    python about.py            writes clip.wav.about.json for the clips below
    python about.py --clear    removes them: the clips are heard knowing only their file's name
"""
import json
import sys

from paths import CLIPS

NOT_SAID = ("Mount Kilimanjaro", "Dr. Patel", "Vienna", "Nairobi")
ABOUT = {
    "en_us_clean": ("Satellites, climate funds and the bhajans of Lakkha Singh",
                    "Eight short readings. Featuring the singer Lakkha Singh. Filmed between "
                    "Vienna and Nairobi with thanks to Dr. Patel."),
    "en_us_over": ("Readings for two voices",
                   "Dr. Moll on what science can and cannot tell us, and more. Not in this "
                   "episode: our trip to Mount Kilimanjaro, see the channel for that."),
    "en_us_long": ("Forty-five readings from the encyclopedia",
                   "With Lakkha Singh, Dr. Moll, the skiers Maciej Krezel and Anna Ogarzynska. "
                   "Recorded in Vienna. Thanks to Dr. Patel."),
    "ar_eg_clean": ("قراءات قصيرة: من كازا برانكا إلى التبت",
                    "ثماني قراءات من الموسوعة، منها تاريخ مدينة كازا برانكا. شكر خاص للدكتور "
                    "باتيل من نيروبي."),
    "en_us_noise": ("Readings over noise",
                    "Recorded outdoors near Mount Kilimanjaro with Dr. Patel, on the road from "
                    "Nairobi to Vienna."),
}


def main() -> None:
    for clip, (title, description) in ABOUT.items():
        target = CLIPS / clip / "clip.wav.about.json"
        if "--clear" in sys.argv:
            target.unlink(missing_ok=True)
            continue
        kept = {"title": title, "by": "Reading Room", "description": description}
        target.write_text(json.dumps(kept, ensure_ascii=False), encoding="utf-8")
        print(clip, "told", flush=True)


if __name__ == "__main__":
    main()
