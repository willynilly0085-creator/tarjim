from tarjim.assistant import mode_for


def test_chat_wording_maps_to_the_right_job_mode() -> None:
    assert mode_for("burned", "clone") == "burn"
    assert mode_for("subtitles", "clone") == "srt"
    assert mode_for("dubbed", "studio") == "dub-studio"
    assert mode_for("dubbed", "robot") == "dub-gemini"
    assert mode_for("dubbed", "natural") == "dub-gemini"
    assert mode_for("anything", "clone") == "burn"
