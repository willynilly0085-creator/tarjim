import pytest

from tarjim.assistant import mode_for


def test_chat_wording_maps_to_the_right_job_mode() -> None:
    assert mode_for("burned") == "burn"
    assert mode_for("subtitles") == "srt"
    assert mode_for("dubbed-studio") == "dub-studio"
    assert mode_for("dubbed-robot") == "dub-gemini"
    assert mode_for("dubbed-natural") == "dub-gemini"
    assert mode_for("dubbed") == "dub-gemini"
    assert mode_for("anything-clone") == "burn"


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


def test_status_can_wait_until_the_job_finishes(monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim import assistant_http

    stages = iter(["hearing", "translating", "done"])
    monkeypatch.setattr(assistant_http, "call", lambda _path: {"stage": (s := next(stages)),
                                                               "finished": s == "done"})
    assert assistant_http.wait_for("abc", 60, tick=0)["stage"] == "done"


QUALITIES = {"title": "talk", "default": "1080", "limit": 8 * 1024 ** 3,
             "audio": {"size": 10 * 2 ** 20},
             "choices": [{"id": "2160", "label": "2160p", "size": 9 * 1024 ** 3},
                         {"id": "1080", "label": "1080p", "size": 128 * 2 ** 20}]}


def chat_engine(monkeypatch: pytest.MonkeyPatch, qualities: object) -> list[tuple[str, object]]:
    from tarjim import assistant

    asked: list[tuple[str, object]] = []

    def call(path: str, body: object = None) -> object:
        asked.append((path, body))
        return qualities if path == "/links/qualities" else {"id": "abc", "stage": "queued"}

    monkeypatch.setattr(assistant, "call", call)
    return asked


def test_a_link_from_chat_waits_for_the_person_to_pick_a_quality(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.assistant import translate_video

    asked = chat_engine(monkeypatch, QUALITIES)
    reply = translate_video("https://youtu.be/x", "ar", "subtitles")
    assert reply["started"] is False and reply["default"] == "1080"
    assert [q["quality"] for q in reply["qualities"]] == ["2160", "1080", "audio"]
    assert reply["qualities"][0]["over_8_gb"] and reply["qualities"][1]["size_mb"] == 128
    assert [path for path, _ in asked] == ["/links/qualities"]
    translate_video("https://youtu.be/x", "ar", "dubbed-clone", "720")
    assert asked[-1] == ("/jobs", {"url": "https://youtu.be/x", "target": "ar",
                                   "mode": "dub-clone", "dialect": "saudi", "quality": "720"})


def test_sound_only_is_offered_in_chat_for_a_subtitle_file_alone(
        monkeypatch: pytest.MonkeyPatch) -> None:
    from tarjim.assistant import translate_video

    chat_engine(monkeypatch, QUALITIES)
    reply = translate_video("https://youtu.be/x", "en", "burned")
    assert [q["quality"] for q in reply["qualities"]] == ["2160", "1080"]


@pytest.mark.parametrize(("qualities", "started", "note"), [
    ({"error": 422, "detail": '{"error": "download"}'}, True, True),
    ({"title": "", "default": "", "choices": [], "audio": None, "limit": 1}, True, False),
    ({"error": 422, "detail": '{"error": "list"}'}, False, False),
    ({"error": "tarjim is not running"}, False, False),
])
def test_a_link_without_qualities_to_pick(monkeypatch: pytest.MonkeyPatch, qualities: object,
                                          started: bool, note: bool) -> None:
    from tarjim.assistant import translate_video

    asked = chat_engine(monkeypatch, qualities)
    reply = translate_video("https://example.com/v.mp4")
    assert (asked[-1][0] == "/jobs") is started and ("note" in reply) is note
