"""The Saudi and standard Arabic buttons never swap places; the last one used is marked."""
import json

import pytest

from tarjim.phone import choice


@pytest.mark.parametrize("last", ["saudi", "msa"])
def test_the_buttons_keep_their_places(last: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(choice, "setting", lambda name: last if name == "phone_dialect" else "")
    rows = json.loads(choice.dialect_keyboard("burn", "k1"))["inline_keyboard"]
    data = [row[0]["callback_data"] for row in rows]
    assert data == ["dl:saudi:burn:k1", "dl:msa:burn:k1"]
    ticked = [row[0]["callback_data"] for row in rows if row[0]["text"].startswith("✓")]
    assert ticked == [f"dl:{last}:burn:k1"]
