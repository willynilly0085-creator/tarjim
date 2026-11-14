"""Whether tarjim translates what a line means or what its words say: lines a word-for-word
translation gets wrong (an idiom, a phrasal verb, sarcasm, a negation that turns the sentence,
a word with two meanings, a number or unit that must come through), each with what it means,
translated by tarjim's own translator with a new user's settings and read by a judge that is
not the translator. The recorded sentences of the bench are an encyclopedia's and have none of
this, so the judge found nothing word for word there.

Text only: no sound is sent, as for an engine that does not hear. A judge is a model too; the
lines it faults are printed to be read.

    python traps.py [label]      kept in runs/_traps/<label>.json
"""
import json
import os
import sys
from collections import Counter
from typing import Any

from paths import RUNS, prepare

prepare()

from tarjim.gemini_client import GeminiClient  # noqa: E402
from tarjim.languages import language  # noqa: E402
from tarjim.models import Cue, Word  # noqa: E402
from tarjim.prefs.active import active, plain, using  # noqa: E402
from tarjim.rules import rules_for  # noqa: E402
from tarjim.translate.prompt import Brief  # noqa: E402
from tarjim.translate.rounds import Rounds  # noqa: E402

Row = dict[str, Any]
SECONDS = 4.0
TRAPS = [  # (kind, what is said, what it means)
    ("idiom", "Honestly, that exam was a piece of cake.", "the exam was very easy"),
    ("idiom", "He finally kicked the bucket last winter.", "he died last winter"),
    ("idiom", "Don't worry, I'll hold down the fort while you're gone.",
     "I will look after things while you are away"),
    ("idiom", "She let the cat out of the bag about the surprise party.",
     "she revealed the secret of the party"),
    ("idiom", "We're not out of the woods yet.", "the danger or difficulty is not over yet"),
    ("idiom", "That car cost him an arm and a leg.", "the car was very expensive"),
    ("idiom", "Break a leg tonight!", "good luck with tonight's performance"),
    ("idiom", "I'm going to hit the sack early.", "I am going to bed early"),
    ("idiom", "It's raining cats and dogs out there.", "it is raining very heavily"),
    ("idiom", "He's been under the weather all week.", "he has been unwell all week"),
    ("phrasal", "The deal fell through at the last minute.", "the deal failed at the last minute"),
    ("phrasal", "She turned down the job offer.", "she refused the job offer"),
    ("phrasal", "I ran into my old teacher at the airport.", "I met my old teacher by chance"),
    ("phrasal", "They called off the wedding.", "they cancelled the wedding"),
    ("phrasal", "He made up the whole story.", "he invented the story; it is not true"),
    ("sarcasm", "Oh great, another meeting. Just what I needed.",
     "the speaker is annoyed at having another meeting; it is not welcome"),
    ("sarcasm", "Yeah, right, like he's ever on time.", "the speaker does not believe he will be"
     " on time; he is always late"),
    ("sarcasm", "Nice job breaking the printer, genius.", "blame, not praise: you broke it"),
    ("negation", "I couldn't agree more.", "I agree completely"),
    ("negation", "I don't think he didn't know.", "I think he knew"),
    ("negation", "It's not that I don't like it, I just can't afford it.",
     "I like it, but I cannot pay for it"),
    ("negation", "You can't be too careful with these machines.",
     "you should be as careful as possible"),
    ("negation", "Hardly anyone showed up.", "almost nobody came"),
    ("two meanings", "The bank was steep, so we sat by the water instead.",
     "bank is the side of a river, not a place for money"),
    ("two meanings", "She's a really cool boss.", "cool means good or relaxed, not cold"),
    ("two meanings", "He's sick! Did you see that goal?", "sick is praise: amazing, not ill"),
    ("two meanings", "I'm dead, that joke was too good.", "I am laughing hard, not dead"),
    ("two meanings", "Can you give me a ring tomorrow?", "phone me tomorrow, not a piece of"
     " jewellery"),
    ("number", "It dropped from 3.5 million to under 900,000 in two years.",
     "the numbers 3.5 million, 900,000 and two years all come through"),
    ("number", "Take two tablets every six hours, never more than eight a day.",
     "two tablets, every six hours, at most eight a day"),
    ("number", "The flight leaves at a quarter to nine, so be there by seven thirty.",
     "leaves at 8:45; be there by 7:30"),
    ("number", "He ran the mile in under four minutes, the first to do it.",
     "one mile, less than four minutes, the first person"),
]
ASKED = """You are checking subtitle translations into {target}. For each numbered item you \
get what was SAID in English, what it MEANS, and the SUBTITLE shown. The subtitle may be in a \
spoken dialect; that is not an error. Answer for each:
- meaning: "right" (a viewer understands what MEANS says), "small" (a shade off, nobody is \
misled), "wrong" (a viewer understands something else, or a number or point is lost).
- literal: true when it carries the English words over where a speaker of {target} would not \
say it that way, whether or not the meaning survives.
- note: a few words in English on what is off; "" when nothing is.

{items}"""
SCHEMA = {"type": "object", "properties": {"items": {"type": "array", "items": {
    "type": "object", "properties": {"number": {"type": "integer"}, "meaning": {"type": "string"},
                                     "literal": {"type": "boolean"}, "note": {"type": "string"}},
    "required": ["number", "meaning", "literal", "note"]}}}, "required": ["items"]}


def lines() -> list[Cue]:
    cues = []
    for n, (_kind, said, _means) in enumerate(TRAPS):
        words = said.split()
        step = (SECONDS - 0.5) / len(words)
        timed = [Word(w, n * SECONDS + k * step, n * SECONDS + (k + 1) * step, "S1")
                 for k, w in enumerate(words)]
        cues.append(Cue(n * SECONDS, n * SECONDS + SECONDS - 0.3, timed))
    return cues


def translated(target: str) -> list[str]:
    """The lines through tarjim's translator, as a job with a new user's settings asks it."""
    prefs, cues = plain(target), lines()
    with using(prefs):
        rules = rules_for(language(target), prefs)
        rounds = Rounds(cues, lambda _start, _end: b"", Brief(
            language(target), "saudi", rules, hears=False, manner=active().translate))
        failures = rounds.run()
        if failures and not rounds.translated():
            raise failures[0]
        rounds.finish(rules)
    return [cue.text for cue in cues]


def judged(texts: list[str], target: str) -> list[Row]:
    os.environ["TARJIM_GEMINI_MODEL"] = "gemini-3.1-pro-preview"  # not the translator
    items = "\n\n".join(f"{n}.\nSAID: {said}\nMEANS: {means}\nSUBTITLE: {text}"
                        for n, ((_kind, said, means), text) in enumerate(
                            zip(TRAPS, texts, strict=True), start=1))
    answer = GeminiClient().ask(ASKED.format(target=language(target).name, items=items), None,
                                SCHEMA)
    found = {int(item["number"]): item for item in answer["items"]}
    return [{"kind": kind, "said": said, "means": means, "subtitle": text,
             **found.get(n, {"meaning": "unjudged", "literal": False, "note": ""})}
            for n, ((kind, said, means), text) in enumerate(zip(TRAPS, texts, strict=True), 1)]


def main() -> None:
    label = sys.argv[1] if len(sys.argv) > 1 else "first"
    kept = RUNS / "_traps" / f"{label}.json"
    if not kept.exists():
        kept.parent.mkdir(parents=True, exist_ok=True)
        rows = judged(translated("ar"), "ar")
        kept.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    rows = json.loads(kept.read_text(encoding="utf-8"))
    for kind in dict.fromkeys(row["kind"] for row in rows):
        mine = [row for row in rows if row["kind"] == kind]
        said = Counter(row["meaning"] for row in mine)
        print(f"{kind:13} {len(mine):2} lines: {dict(said)}, "
              f"{sum(bool(row['literal']) for row in mine)} word for word")
    for row in rows:
        if row["meaning"] != "right" or row["literal"]:
            print(f"- [{row['kind']}] {row['said']}\n    {row['subtitle']}\n    {row['meaning']}"
                  f"{', word for word' if row['literal'] else ''}: {row['note']}")


if __name__ == "__main__":
    main()
