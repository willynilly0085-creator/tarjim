"""The review of 2026-10-29 on the page and the extension: a right-click on a feed finds its post,
every refusal has its own words, Cancel asks first, and nothing waits forever in silence."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from tarjim.ui_languages import FOLDER, codes

ROOT = Path(__file__).resolve().parents[1] / "tarjim"
EXTENSION = ROOT / "extension"
PAGE = ROOT / "web"
NODE = shutil.which("node")


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extension_words(code: str) -> dict[str, str]:
    raw = json.loads(source(EXTENSION / "_locales" / code / "messages.json"))
    return {key: entry["message"] for key, entry in raw.items()}


POSTS_CHECK = """
const posts = await import(process.argv[1]);
let asked = 0;
globalThis.chrome = { scripting: { executeScript: async () => { asked += 1;
  return [{ result: "https://www.tiktok.com/@a/video/1" }]; } } };
const tiktok = "https://v16-webapp-prime.tiktok.com/video/tos/maliva/abc/?mime_type=video_mp4";
const found = await posts.clickedPost({ srcUrl: tiktok }, { id: 4 });
const direct = await posts.clickedPost({ srcUrl: "https://example.com/v.mp4" }, { id: 4 });
console.log(JSON.stringify({ found, direct, asked,
  facebook: posts.downloadable("https://www.facebook.com/watch/?v=1234"),
  feed: posts.downloadable("https://www.tiktok.com/foryou"), cdn: posts.downloadable(tiktok) }));
"""


@pytest.mark.skipif(not NODE, reason="needs node")
def test_a_right_click_on_a_tiktok_feed_or_a_facebook_video_finds_the_post() -> None:
    url = (EXTENSION / "posts.js").as_uri()
    done = subprocess.run([str(NODE), "--input-type=module", "-e", POSTS_CHECK, url],
                          capture_output=True, text=True, check=True, timeout=60)
    seen = json.loads(done.stdout)
    assert seen == {"found": "https://www.tiktok.com/@a/video/1", "direct": "", "asked": 1,
                    "facebook": True, "feed": False, "cdn": False}


def test_every_refusal_the_extension_knows_has_words_in_every_language() -> None:
    upload = source(EXTENSION / "upload.js")
    table = upload.split("REFUSED = ")[1].split("};")[0]
    mapped = dict(re.findall(r'"?(\w+(?: \w+)?)"?: "(\w+)"', table))
    assert {"bad url", "file", "big", "list", "dub_language", "dub_key", "mode"} <= set(mapped)
    assert "sendProblem(error, state.languages.get(options.target))" in source(EXTENSION / "app.js")
    for code in codes():
        words = extension_words(code)
        page = json.loads(source(FOLDER / f"{code}.json"))
        assert set(mapped.values()) <= set(words), code
        assert "$LANGUAGE$" in words["sendDubLanguage"], code
        assert words["sendDubKey"] == page["sendDubKey"] and words["openSrt"] == page["openSrt"]


def test_cancel_in_the_extension_asks_first_and_a_subtitle_file_opens_as_text() -> None:
    jobs = source(EXTENSION / "jobs.js")
    assert '["cancel", "cancelSure", "cancelLabel"]' in jobs
    assert 'job.mode === "srt" ? "openSrt" : "play"' in jobs


def test_a_right_clicked_link_waits_as_long_as_pairing_may() -> None:
    assert "const FRESH = 10 * 60 * 1000;" in source(EXTENSION / "source.js")
    lifetime = re.search(r"LIFETIME = ([\d.]+)", source(ROOT / "server" / "pairing.py"))
    assert lifetime and float(lifetime.group(1)) == 600
    assert "startJob" not in source(EXTENSION / "pairing.js")


def test_the_page_says_when_tarjim_cannot_be_reached_or_a_step_stopped() -> None:
    finish = source(PAGE / "assistant_finish.js")
    assert '"sendOffline"' in finish and '"progressStopped"' in finish
    assert "tool.state !== \"downloading\"" in finish  # idle after a restart counts as stopped
    assert 'button(t("tryAgain"), showPlan' in source(PAGE / "assistant.js")
    jobs = source(PAGE / "jobs.js")
    assert "jobs-offline" in jobs and 'classList.toggle("stale"' in jobs
    assert ".jobs.stale .job" in source(PAGE / "web.css")
    signin = source(PAGE / "signin.js")
    assert "gaveUp()" in signin and 'sent ? "signInWaiting" : "signInFailed"' in signin
