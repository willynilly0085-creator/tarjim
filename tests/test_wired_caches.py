"""A kept decision about where the subtitle goes, and what was seen to make it, serve only the
layout they were made for; one kept before the settings serves the default layout (2026-11-09)."""
import json
from pathlib import Path

from tarjim.job import Job
from tarjim.models import Cue
from tarjim.prefs.model import resolve
from tarjim.render import moments, placement
from tarjim.render.ass import Canvas

WIDER = Canvas.drawn((640, 360), resolve({"look.side_margin": 10}, {}, "ar").look, "Dubai")
STEADY = Canvas.drawn((640, 360), resolve({"look.position": "steady"}, {}, "ar").look, "Dubai")


def kept_place(folder: Path, layout: str | None) -> Path:
    record = folder / placement.KEPT
    data = {"bands": [[0.85, 0.95]], "top": False, "margin": 90}
    record.write_text(json.dumps(data if layout is None else {**data, "layout": layout}),
                      encoding="utf-8")
    return record


def test_a_kept_place_serves_its_own_layout_only(tmp_path: Path) -> None:
    usual = Canvas(640, 360)
    older = kept_place(tmp_path, None)  # written before 2026-11-09: the default layout
    found = placement.kept(older, usual)
    assert found is not None and found.margin_v == 90
    assert placement.kept(older, WIDER) is None
    assert placement.kept(kept_place(tmp_path, WIDER.layout), WIDER) is not None
    assert placement.kept(kept_place(tmp_path, WIDER.layout), usual) is None


def test_what_was_seen_serves_its_own_layout_only(tmp_path: Path) -> None:
    record = tmp_path / moments.KEPT
    seen = {1.0: [(0.8, 0.9)]}
    moments.keep(record, seen, WIDER)
    assert moments.kept(record, WIDER) == seen and moments.kept(record, Canvas(640, 360)) is None
    record.write_text(json.dumps({"seen": [[1.0, [[0.8, 0.9]]]]}), encoding="utf-8")
    assert moments.kept(record, Canvas(640, 360)) == seen


def test_a_steady_place_moves_no_single_line(tmp_path: Path) -> None:
    job = Job(tmp_path / "v.mp4", cache_dir=tmp_path / "cache")
    cues = [Cue(0.0, 1.0, text="كلام")]
    assert moments.moved(job, cues, STEADY, None) == STEADY
    assert not (job.cache / moments.KEPT).exists()
