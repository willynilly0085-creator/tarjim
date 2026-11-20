"""A model that was never downloaded is named as a missing part, not as a link that failed.

Seen 2026-11-20 on the owner's new Mac: Hugging Face's own words for a model not on the disk,
with downloads turned off ("...outgoing traffic has been disabled. To enable repo look-ups and
downloads online..."), were read as a failed download, and the page told him to check his link.
"""
import json
from pathlib import Path

import tarjim
from tarjim.server.reasons import classify

HUGGING_FACE = ("Cannot find an appropriate cached snapshot folder for the specified revision "
                "on the local disk and outgoing traffic has been disabled. To enable repo "
                "look-ups and downloads online, pass 'local_files_only=False' as input.")
HERE = Path(tarjim.__file__).resolve().parent


class LocalEntryNotFoundError(Exception):
    pass


def test_a_model_not_on_the_disk_is_a_missing_part() -> None:
    assert classify(LocalEntryNotFoundError(HUGGING_FACE)) == "parts"
    assert classify(RuntimeError("ERROR: unable to download video data: HTTP 403")) == "download"


def test_every_language_says_it_on_the_page_in_the_add_on_and_on_the_phone() -> None:
    for page in (HERE / "web" / "i18n").glob("*.json"):
        assert json.loads(page.read_text(encoding="utf-8")).get("err_parts"), page.name
    for words in (HERE / "extension" / "_locales").glob("*/messages.json"):
        assert json.loads(words.read_text(encoding="utf-8"))["errParts"]["message"], words
    assert '"parts"' in (HERE / "web" / "jobs.js").read_text(encoding="utf-8")
    assert 'parts: "errParts"' in (HERE / "extension" / "shared.js").read_text(encoding="utf-8")
