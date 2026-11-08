"""Where files go and how they are written follow the person's settings, each order runs with
the settings it was made with, and a dub sounds as they set it (2026-11-09)."""
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from tarjim.dub import clone, mix
from tarjim.dub.gemini_voice import style_for
from tarjim.dub.lines import Line
from tarjim.job import Job
from tarjim.prefs.active import using
from tarjim.prefs.model import resolve
from tarjim.render import burn
from tarjim.render.encoders import for_quality
from tarjim.render.sharp import enlarged
from tarjim.server import engine, job_record
from tarjim.server.job_routes import refusal
from tarjim.server.jobs import Order, Task
from tarjim.server.orders import order_from, stamped
from tests.test_mark import outputs


def test_a_small_picture_is_enlarged_to_the_chosen_frame_or_left_alone() -> None:
    assert enlarged((848, 464)) == enlarged((848, 464), "1080")
    small = enlarged((848, 464), "720")
    assert small is not None and (small.width, small.height) == (1280, 700)
    assert enlarged((848, 464), "off") is None


def test_a_higher_quality_aims_lower() -> None:
    assert for_quality(0)[0][6:8] == ["-cq", "21"] and for_quality(0)[3][2:4] == ["-crf", "19"]
    high = for_quality(0, "high")
    assert high[0][6:8] == ["-cq", "18"] and high[3][2:4] == ["-crf", "16"]


def burned_with(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, values: dict[str, Any]) -> str:
    seen: list[list[str]] = []

    def fake_run(argv: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        seen.append(argv)
        Path(argv[-1]).write_bytes(b"video")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(burn, "run", fake_run)
    monkeypatch.setattr(burn, "video_kbps", lambda _video: 1000)
    monkeypatch.setattr(burn, "codec", lambda _video: "h264")
    monkeypatch.setattr(burn, "sound_codecs", lambda _video: ["aac"])
    monkeypatch.setattr(burn, "tool", lambda name: name)
    ass = "[Script Info]\nPlayResX: 640\nPlayResY: 360\n"
    with using(resolve(values, {}, "ar")):
        burn.burn(tmp_path / "v.mp4", ass, tmp_path / "out.mp4")
    return " ".join(seen[0])


def test_the_burn_takes_the_chosen_quality_and_enlargement(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    usual = burned_with(tmp_path, monkeypatch, {})
    assert "scale=1920:1080" in usual and "-cq 21" in usual and "-maxrate 3450k" in usual
    chosen = burned_with(tmp_path, monkeypatch, {"output.quality": "high",
                                                 "output.enlarge": "off"})
    assert "scale=" not in chosen and "-cq 18" in chosen and "-maxrate 1600k" in chosen


def test_another_dialect_is_named_in_the_files() -> None:
    assert Job(Path("clip.mp4")).output(".srt").name == "clip.ar.srt"
    assert Job(Path("clip.mp4"), dialect="msa").output(".srt").name == "clip.ar.msa.srt"
    assert Job(Path("clip.mp4"), "en", dialect="msa").output(".srt").name == "clip.en.srt"


def test_the_ass_file_is_kept_only_when_asked(tmp_path: Path,
                                              monkeypatch: pytest.MonkeyPatch) -> None:
    chosen = resolve({"output.keep_ass": False}, {}, "ar")
    job = Job(tmp_path / "v.mp4", out_dir=tmp_path, cache_dir=tmp_path / "cache", prefs=chosen)
    with using(chosen):
        burned = outputs(tmp_path, monkeypatch, job)
    assert not job.output(".ass").exists() and job.output(".srt").exists()
    assert "Dialogue:" in burned[0][1]


def made_job(tmp_path: Path, order: Order) -> Job:
    task = Task(order)
    return engine.job_for(task, tmp_path / "v.mp4", tmp_path / "usual")


def test_a_dub_is_clean_or_subtitled_as_the_order_says(tmp_path: Path) -> None:
    usual = stamped(Order("v.mp4", mode="dub-gemini"))
    clean = stamped(Order("v.mp4", mode="dub-gemini", tweaks={"output.burn_with_dub": False}))
    assert made_job(tmp_path, usual).burn and not made_job(tmp_path, clean).burn
    assert not made_job(tmp_path, stamped(Order("v.mp4", mode="srt"))).burn


def test_files_go_to_the_orders_folder_or_the_usual_one_once_it_is_gone(tmp_path: Path) -> None:
    mine = tmp_path / "mine"
    mine.mkdir()
    order = Order("v.mp4", prefs={"version": 1, "values": {"output.folder": str(mine)}})
    assert made_job(tmp_path, order).out_dir == mine
    mine.rmdir()
    assert made_job(tmp_path, order).out_dir == tmp_path / "usual"
    assert made_job(tmp_path, stamped(Order("v.mp4"))).out_dir == tmp_path / "usual"


def test_an_order_keeps_its_settings_through_jobs_json_and_a_retry(tmp_path: Path) -> None:
    order = stamped(order_from("v.mp4", {"tweaks": {"look.size_wide": 110}}))
    assert order.prefs == {"version": 1, "values": {"look.size_wide": 110}}
    row = json.loads(json.dumps({"id": "a", "error": "", "error_code": "", "failed_at": "",
                                 "created": 1.0, "stage": "failed", "video": "",
                                 "outputs": [], "order": order.__dict__}))
    again = job_record.task_from(row).order
    assert again == order and stamped(again) == order
    assert made_job(tmp_path, again).settings.look.size_wide == 110


def test_an_order_with_a_change_that_cannot_be_made_is_refused_up_front() -> None:
    assert refusal(order_from("v.mp4", {"tweaks": {"look.size_wide": 110}})) == ""
    for wrong in ({"look.size_wide": 300}, {"nothing.here": 1}, {"output.folder": "C:/"}):
        assert refusal(order_from("v.mp4", {"tweaks": wrong})) == "tweaks", wrong


def test_the_background_under_a_dub_follows_the_balance() -> None:
    background = np.full((100, 2), 0.5, dtype=np.float32)
    line = Line(0.0, 0.001, "", "")
    usual = mix.mix([line], [np.zeros(0, dtype=np.float32)], background)
    with using(resolve({"dub.balance": 40}, {}, "ar")):
        lower = mix.mix([line], [np.zeros(0, dtype=np.float32)], background)
    assert np.allclose(usual, 0.5) and np.allclose(lower, 0.2)


def test_the_gemini_voices_take_the_chosen_tone() -> None:
    usual = style_for("ar", "saudi")
    assert usual.startswith("natural and expressive, like a professional voice actor")
    assert style_for("ar", "saudi", "natural") == usual
    assert style_for("ar", "saudi", "news").startswith("clear and steady")
    assert usual.endswith("a natural Saudi Arabic accent")


def test_a_cloned_voice_takes_the_chosen_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    steps: list[int] = []

    class Model:
        def generate(self, **asked: Any) -> np.ndarray:
            steps.append(asked["inference_timesteps"])
            return np.zeros(10, dtype=np.float32)

    voices = clone.CloneVoices.__new__(clone.CloneVoices)
    voices.model, voices.rate, voices.references = Model(), 16000, {"S1": "s1.wav"}
    voices.once(Line(0.0, 1.0, "S1", "مرحبا"))
    with using(resolve({"dub.clone_steps": 16}, {}, "ar")):
        voices.once(Line(0.0, 1.0, "S1", "مرحبا"))
    assert steps == [clone.STEPS, 16]
