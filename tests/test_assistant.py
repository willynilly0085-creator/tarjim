import pytest

from tarjim.assistant import mode_for


def test_chat_wording_maps_to_the_right_job_mode() -> None:
    assert mode_for("burned", "clone") == "burn"
    assert mode_for("subtitles", "clone") == "srt"
    assert mode_for("dubbed", "studio") == "dub-studio"
    assert mode_for("dubbed", "robot") == "dub-gemini"
    assert mode_for("dubbed", "natural") == "dub-gemini"
    assert mode_for("anything", "clone") == "burn"


def test_chat_can_read_the_subtitles_of_a_finished_job(monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim import assistant

    job = {"stage": "done", "files": ["C:\\out\\clip.ar.mp4", "C:\\out\\clip عربي.ar.srt"]}
    monkeypatch.setattr(assistant, "call", lambda path, body=None: job)
    asked: list[str] = []
    monkeypatch.setattr(assistant, "fetch_text", lambda path: asked.append(path) or "1\n00:00")
    assert assistant.read_subtitles("abc123abc123") == "1\n00:00"
    assert asked == ["/files/abc123abc123/clip%20%D8%B9%D8%B1%D8%A8%D9%8A.ar.srt"]


def test_unknown_actions_are_refused_before_reaching_the_server() -> None:
    from tarjim.assistant import control_translation

    assert "error" in control_translation("abc123abc123", "delete")
