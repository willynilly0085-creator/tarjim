"""The words that say a model other than the one picked translated the job, in every language
of tarjim's page and of the extension, and both of them run (2026-11-19, test_picked_model_note.py
for the engines)."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tarjim.ui_languages import FOLDER

ROOT = Path(__file__).resolve().parents[1] / "tarjim"
LOCALES = ROOT / "extension" / "_locales"
EMOJI = re.compile("[🌀-🫿☀-➿]")


@pytest.mark.parametrize("path", sorted(FOLDER.glob("*.json")), ids=lambda p: p.stem)
def test_every_page_language_names_both_models(path: Path) -> None:
    words = json.loads(path.read_text(encoding="utf-8"))["note_other_model"]
    assert "{picked}" in words and "{used}" in words and not EMOJI.search(words)


@pytest.mark.parametrize("folder", sorted(LOCALES.iterdir()), ids=lambda p: p.name)
def test_every_extension_language_names_both_models(folder: Path) -> None:
    entry = json.loads((folder / "messages.json").read_text(encoding="utf-8"))["jobOtherModel"]
    assert "$PICKED$" in entry["message"] and "$USED$" in entry["message"]
    assert entry["placeholders"] == {"picked": {"content": "$1"}, "used": {"content": "$2"}}
    assert not EMOJI.search(entry["message"])


def test_the_arabic_words_are_saudi() -> None:
    page = json.loads((FOLDER / "ar.json").read_text(encoding="utf-8"))["note_other_model"]
    extension = json.loads((LOCALES / "ar" / "messages.json").read_text(encoding="utf-8"))
    assert "اخترته" in page and "اخترته" in extension["jobOtherModel"]["message"]


SHOWN = """
const { readFileSync } = await import("node:fs");
const [notesUrl, i18nUrl, wordsPath, summaryUrl, extensionPath] = process.argv.slice(1);
globalThis.document = { documentElement: { lang: "", dir: "" }, querySelectorAll: () => [],
  createElement: (tag) => ({ tag }) };
globalThis.fetch = async () => ({ json: async () => JSON.parse(readFileSync(wordsPath, "utf8")) });
const own = JSON.parse(readFileSync(extensionPath, "utf8"));
globalThis.chrome = { i18n: { getUILanguage: () => "ar", getMessage: (key, subs) =>
  own[key].message.replace(/\\$(\\w+)\\$/g, (_, name) =>
    subs[Number(own[key].placeholders[name.toLowerCase()].content.slice(1)) - 1]) } };
await (await import(i18nUrl)).load("ar");
const notes = await import(notesUrl);
const summary = await import(summaryUrl);
const other = { kind: "other_model", problem: false, count: 1, at: [],
  picked: "Gemini 4 Hydrogen", used: ["Gemini 3.8 Flash", "Qwen3:8b"] };
const list = { dataset: {}, hidden: true, items: [],
  replaceChildren(...items) { this.items = items; } };
const done = { stage: "done", notes: [other] };
notes.showNotes({ dataset: {}, querySelector: () => list }, done);
const line = { hidden: true, textContent: "" };
summary.showNotes({ querySelector: () => line }, done);
const items = list.items.map((li) => [li.className, li.textContent]);
const seen = { label: notes.stageLabel(done), items,
  extension: line.textContent, shown: !line.hidden };
summary.showNotes({ querySelector: () => line }, { stage: "translating", notes: [other] });
console.log(JSON.stringify({ ...seen, afterwards: line.hidden }));
"""


@pytest.mark.skipif(not shutil.which("node"), reason="needs node")
def test_the_page_and_the_extension_say_which_model_translated() -> None:
    """Both, run: the names said in the person's words, each kept left to right inside Arabic,
    and the job stays plain done (the subtitles are not wrong, the model is not the one picked)."""
    args = [str(shutil.which("node")), "--input-type=module", "-e", SHOWN,
            (ROOT / "web" / "notes.js").as_uri(), (ROOT / "web" / "i18n.js").as_uri(),
            str(FOLDER / "ar.json"), (ROOT / "extension" / "summary.js").as_uri(),
            str(LOCALES / "ar" / "messages.json")]
    seen = json.loads(subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                                     check=True, timeout=60).stdout)
    ar = json.loads((FOLDER / "ar.json").read_text(encoding="utf-8"))
    assert seen["label"] == ar["stage_done"]
    [(style, text)] = seen["items"]
    assert style == "note-quiet" and kept("Gemini 4 Hydrogen") in text
    assert kept("Gemini 3.8 Flash") in text and kept("Qwen3:8b") in text
    assert "اخترته" in text and "{" not in text
    assert kept("Gemini 4 Hydrogen") in seen["extension"] and "اخترته" in seen["extension"]
    assert kept("Gemini 3.8 Flash") in seen["extension"] and seen["shown"]
    assert seen["afterwards"] is True  # a job still running shows none


def kept(name: str) -> str:
    """A model's name held left to right, so its digits stay in order inside Arabic."""
    return f"{chr(0x2066)}{name}{chr(0x2069)}"  # left-to-right isolate, then its end
