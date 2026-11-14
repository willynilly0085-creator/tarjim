"""Whether each sentence's subtitle means what was said: read by a model that is not the one
that translated, with what a person wrote was said and a person's own translation beside it.

For every sentence of a clip the judge gets four texts: what was said (the truth), a
translator's version of it (FLEURS; formal language, where tarjim may write a dialect, which is
no fault), what tarjim heard, and the subtitle tarjim showed while it was said. It answers, for
the subtitle against what was SAID: is the meaning right, slightly off, or wrong; does it read
word for word instead of the way people say it; is something left out; is something there that
was not said (a line written twice counts); and when it is not right, whether tarjim heard it
wrong or translated it wrong. The verdicts are kept in meaning.json beside the run's result.

A judge is a model too: its verdicts are a measure to compare runs by and to read a sample
of, not the truth about any one line.

    python judge.py [--label L] [clip ...]
"""
import argparse
import json
import os
from collections import Counter
from typing import Any

from paths import CLIPS, RUNS, prepare

prepare()
os.environ.setdefault("TARJIM_GEMINI_MODEL", "gemini-3.1-pro-preview")  # not the translator

from score import Scored  # noqa: E402

from tarjim.gemini_client import GeminiClient  # noqa: E402

Row = dict[str, Any]
ASKED = """You are checking subtitles. For each numbered item you get:
SAID: what the speaker really said (written by a person; this is the truth).
REFERENCE: a professional translation of SAID into the target language, in formal language.
HEARD: what the subtitling system heard.
SUBTITLE: what the system showed, in the target language. It may be in a spoken dialect; a
dialect, a different style or different word order is NOT an error.

Judge SUBTITLE against the meaning of SAID (REFERENCE only helps you understand SAID):
- meaning: "right" (a viewer understands what was said), "small" (a detail or shade is off but
  nobody is misled), "wrong" (says something else, or a main point, name or number is lost).
- literal: true when it follows the source word for word where a speaker of the target language
  would say it differently (a calque, an idiom carried over as words).
- left_out: true when part of what was said is missing.
- added: true when it holds something that was not said, or says the same thing twice.
- cause: when meaning is not "right": "hearing" if HEARD already differs from SAID in that
  point, else "translation". Otherwise "".
- note: a few words in English saying what is off; "" when nothing is.
Target language: {target}.

{items}"""
SCHEMA = {"type": "object", "properties": {"items": {"type": "array", "items": {
    "type": "object", "properties": {
        "number": {"type": "integer"}, "meaning": {"type": "string"},
        "literal": {"type": "boolean"}, "left_out": {"type": "boolean"},
        "added": {"type": "boolean"}, "cause": {"type": "string"}, "note": {"type": "string"}},
    "required": ["number", "meaning", "literal", "left_out", "added", "cause", "note"]}}},
    "required": ["items"]}
TARGETS = {"ar": "Arabic", "en": "English"}


def owners(one: Scored) -> dict[int, int]:
    """Each line's sentence: the one most of its words stand for; a line none of whose words
    was said goes with the line before it."""
    votes: dict[int, Counter[int]] = {}
    for said, (_unit, line, _word) in one.stood.items():
        votes.setdefault(line, Counter())[one.said[said][1]] += 1
    found, last = {}, 0
    for line in range(len(one.result["cues"])):
        last = votes[line].most_common(1)[0][0] if line in votes else last
        found[line] = last
    return found


def shown(one: Scored) -> list[Row]:
    """Each sentence with what tarjim heard and showed for it, and the lines that showed it."""
    mine: dict[int, list[int]] = {}
    for line, sentence in owners(one).items():
        mine.setdefault(sentence, []).append(line)
    cues = one.result["cues"]
    return [{"said": fact["text"], "reference": fact["reference"],
             "lines": [line + 1 for line in mine.get(k, [])],
             "heard": " ".join(cues[line]["source"] for line in mine.get(k, [])),
             "subtitle": " ".join(cues[line]["text"] for line in mine.get(k, []))}
            for k, fact in enumerate(one.truth["sentences"])]


def judged(name: str, label: str, client: GeminiClient) -> list[Row] | None:
    kept = RUNS / label / name / "meaning.json"
    result = RUNS / label / name / "result.json"
    if kept.exists():
        return list(json.loads(kept.read_text(encoding="utf-8")))
    if not result.exists() or "error" in (found := json.loads(result.read_text(encoding="utf-8"))):
        return None
    truth = json.loads((CLIPS / name / "truth.json").read_text(encoding="utf-8"))
    rows = shown(Scored(truth, found))
    items = "\n\n".join(f"{n}.\nSAID: {row['said']}\nREFERENCE: {row['reference']}\n"
                        f"HEARD: {row['heard']}\nSUBTITLE: {row['subtitle']}"
                        for n, row in enumerate(rows, start=1))
    answer = client.ask(ASKED.format(target=TARGETS[truth["target"]], items=items), None, SCHEMA)
    verdicts = {int(item["number"]): item for item in answer["items"]}
    rows = [{**row, **verdicts.get(n, {"meaning": "unjudged"})}
            for n, row in enumerate(rows, start=1)]
    kept.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("clips", nargs="*")
    parser.add_argument("--label", default="first")
    args = parser.parse_args()
    client = GeminiClient()
    names = args.clips or sorted(p.name for p in (RUNS / args.label).iterdir() if p.is_dir())
    for name in names:
        rows = judged(name, args.label, client)
        if rows is not None:
            said = Counter(row["meaning"] for row in rows)
            print(f"{name}: {dict(said)} by {client.model_used or 'kept'}", flush=True)


if __name__ == "__main__":
    main()
