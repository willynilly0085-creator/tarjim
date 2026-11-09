"""The settings page (2026-11-09), run under node against a pretend engine that answers with the
real settings table: a change saves on its own once, 400 ms after the last move; a refusal
shows its Arabic reason under the setting and the control goes back to what is saved; a preset
is one press and a refused name says why; reset is one setting, one tab or everything, and
everything asks first with the count."""
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tarjim.prefs.table import SPECS
from tarjim.server.listener import OnlyListener
from tarjim.ui_languages import FOLDER, codes

HERE = Path(__file__).resolve().parent
WEB = HERE.parent / "tarjim" / "web"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(not NODE, reason="needs node")
AR = json.loads((FOLDER / "ar.json").read_text(encoding="utf-8"))
EMOJI = re.compile("[\U0001f300-\U0001faff☀-➿]")


def run_page(scenario: str, tmp_path: Path) -> dict[str, Any]:
    from tarjim.prefs.view import state

    kept = tmp_path / "state.json"
    kept.write_text(json.dumps(state("ar"), ensure_ascii=False), encoding="utf-8")
    args = [str(NODE), str(HERE / "prefs_page.mjs"), (HERE / "fake_dom.mjs").as_uri(),
            WEB.as_uri(), str(FOLDER / "ar.json"), str(kept), scenario]
    done = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", check=True,
                          timeout=60)
    return dict(json.loads(done.stdout))


@needs_node
@pytest.mark.usefixtures("prefs_home")
def test_a_change_saves_on_its_own_once_after_the_last_move(tmp_path: Path) -> None:
    seen = run_page("autosave", tmp_path)
    assert seen["early"] == 0  # nothing sent while the slider was still moving
    assert seen["posts"] == [["POST", "/prefs", {"values": {"look.size_wide": 115},
                                                 "language": "ar"}]]
    assert seen["status"] == AR["prefsSaved"] and seen["readout"] == "115%"


@needs_node
@pytest.mark.usefixtures("prefs_home")
def test_a_refused_value_says_why_under_it_and_nothing_of_it_stays(tmp_path: Path) -> None:
    seen = run_page("refusal", tmp_path)
    assert seen["posts"] == [["POST", "/prefs", {"values": {"look.text_colour": "#151413"},
                                                 "language": "ar"}]]
    assert seen["refusal"] == "«لون الكلام»: ما يبان فوق الخلفية."
    assert seen["hidden"] is False and seen["flag"] == "true"
    assert seen["kept"] == "#F7F5F0"  # back to the saved colour
    assert seen["status"] == AR["prefsRefusedSome"].replace("{n}", "1")


@needs_node
@pytest.mark.usefixtures("prefs_home")
def test_a_preset_is_one_press_and_a_refused_name_says_why(tmp_path: Path) -> None:
    seen = run_page("presets", tmp_path)
    assert [p[1:] for p in seen["posts"]] == [["/prefs/preset", {"name": "calm"}],
                                             ["/prefs/preset", {"save_as": "calm"}]]
    assert seen["pressed"] == [AR["preset_calm"]]
    assert seen["usedStatus"] == AR["prefsUsed"].replace("{name}", AR["preset_calm"])
    assert seen["refusedStatus"] == "هالاسم لمجموعة من ترجم نفسه، اختر اسم ثاني."
    assert seen["formOpen"] is True


@needs_node
@pytest.mark.usefixtures("prefs_home")
def test_reset_is_one_setting_one_tab_or_everything_after_one_question(tmp_path: Path) -> None:
    seen = run_page("reset", tmp_path)
    assert [p[1:] for p in seen["posts"]] == [
        ["/prefs/reset", {"keys": ["look.size_wide"], "language": "ar"}],
        ["/prefs/reset", {"group": "look", "language": "ar"}],
        ["/prefs/reset", {"all": True}]]
    assert seen["before"] == 2  # everything waited for the answer to the question
    assert AR["prefsResetAllSure"].replace("{n}", "2") in seen["question"]
    assert seen["status"] == AR["prefsResetDone"]


@needs_node
@pytest.mark.usefixtures("prefs_home")
def test_a_decimal_is_sent_as_the_slider_shows_it(tmp_path: Path) -> None:
    """17.0 reaches the script as 17: rounding by the default sent 18, 0 and 7 (2026-11-09)."""
    seen = run_page("decimals", tmp_path)
    assert seen["posts"] == [["POST", "/prefs", {"values": {
        "text.reading_cps": 17.5, "timing.join_gap": 0.4, "timing.max_duration": 6.5},
        "language": "ar"}]]
    assert seen["readout"].startswith("17.5")


@needs_node
@pytest.mark.usefixtures("prefs_home")
def test_everything_counts_and_names_other_languages_values(tmp_path: Path) -> None:
    seen = run_page("resetElsewhere", tmp_path)
    others = AR["prefsResetAllOthers"]
    # only another language's value changed: still asked, not "everything is original"
    assert seen["only"]["status"] != AR["prefsNothingChanged"]
    assert AR["prefsResetAllSure"].replace("{n}", "1") in seen["only"]["question"]
    assert others in seen["only"]["question"]
    assert AR["prefsResetAllSure"].replace("{n}", "3") in seen["more"]["question"]
    assert others in seen["more"]["question"]
    assert [p[1:] for p in seen["posts"]] == [["/prefs/reset", {"all": True}]]


def test_every_setting_has_words_in_every_interface_language() -> None:
    for code in codes():
        words = json.loads((FOLDER / f"{code}.json").read_text(encoding="utf-8"))
        for key, spec in SPECS.items():
            assert words.get(f"pref_{key}", "").strip(), (code, key)
            # a dash is shown as itself: it is what the person will see on the video
            named = [c for c in spec.choices if str(c).strip().replace(".", "").isalnum()]
            # named as the page's script writes a number: 1.0 is "1"
            names = [f"choice_{key}_{c:g}" if isinstance(c, float) else f"choice_{key}_{c}"
                     for c in named if spec.kind == "choice"]
            assert all(words.get(name, "").strip() for name in names), (code, key)
    page = [v for k, v in AR.items() if k.startswith(("pref", "hint_", "choice_", "tab_",
                                                       "tweaks", "preset_"))]
    assert not [text for text in page if EMOJI.search(text)]


def test_the_page_loads_all_its_scripts_without_being_turned_away() -> None:
    """Forty-odd scripts ask at once; the default queue of 5 refused some on Windows."""
    assert len(list(WEB.glob("*.js"))) > OnlyListener.request_queue_size // 2
    assert OnlyListener.request_queue_size >= 64
