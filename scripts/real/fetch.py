"""Real speech with what was said written by people, and the same sentences translated by
people: FLEURS (Google, CC-BY-4.0), read through the Hugging Face dataset viewer so only the
sentences used are downloaded, not a language's whole archive.

Every FLEURS sentence has a number shared by all its languages (it is a FLoRes sentence), so a
sentence heard in French has its Arabic written by a translator under the same number. For each
language asked: its validation sentences' text (rows.json), and the sound of the first `count`
of them that the reference languages have too.

    python fetch.py en_us fr_fr ... [--count 12] [--references ar_eg en_us]
"""
import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from paths import MATERIAL

VIEWER = "https://datasets-server.huggingface.co/rows"
PAGE = 100
AGENT = {"User-Agent": "speech-bench"}
Row = dict[str, Any]


def get(url: str, tries: int = 4) -> bytes:
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=AGENT),
                                        timeout=90) as reply:
                return bytes(reply.read())
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    raise OSError(url)


def page(language: str, offset: int) -> tuple[list[Row], int]:
    query = urllib.parse.urlencode({"dataset": "google/fleurs", "config": language,
                                    "split": "validation", "offset": offset, "length": PAGE})
    found = json.loads(get(f"{VIEWER}?{query}"))
    return [row["row"] for row in found["rows"]], int(found["num_rows_total"])


def rows_of(language: str) -> list[Row]:
    """Every validation sentence of the language; kept, so it is asked once."""
    kept = MATERIAL / language / "rows.json"
    if kept.exists():
        return list(json.loads(kept.read_text(encoding="utf-8")))
    rows, total = page(language, 0)
    while len(rows) < total:
        rows += page(language, len(rows))[0]
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def sound(language: str, row: Row, index: int) -> Path:
    """One recording of the sentence. A link in rows.json is good for a while only; one that
    has gone is asked again by deleting rows.json."""
    target = MATERIAL / language / f"{row['id']}-{index}.wav"
    if not target.exists():
        target.write_bytes(get(row["audio"][0]["src"]))
    return target


def fetch(language: str, count: int, shared: set[int]) -> int:
    done: set[int] = set()
    for index, row in enumerate(rows_of(language)):
        if len(done) >= count:
            break
        if row["id"] in shared and row["id"] not in done:  # one voice a sentence
            sound(language, row, index)
            done.add(row["id"])
    return len(done)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("languages", nargs="+")
    parser.add_argument("--count", type=int, default=12)
    parser.add_argument("--references", nargs="+", default=["ar_eg", "en_us"])
    args = parser.parse_args()
    shared = set.intersection(*({row["id"] for row in rows_of(ref)} for ref in args.references))
    for language in args.languages:
        try:
            print(language, fetch(language, args.count, shared), "sentences", flush=True)
        except OSError as error:  # the viewer fails on a language now and then: the rest go on
            print(f"{language}: not fetched ({error})", flush=True)


if __name__ == "__main__":
    main()
