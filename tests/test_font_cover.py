"""The settings page lists, and a save accepts, only the fonts on this computer that write the
language's letters (2026-11-09): libass draws a font without them as boxes. Each font here is
made in the test, so nothing depends on what the computer has installed."""
import struct
from pathlib import Path

import pytest

from tarjim.render import font_cover
from tarjim.render.sfnt import covers, read

ARABIC, LATIN = [(0x0600, 0x06FF)], [(0x20, 0x7E)]


def name_table(family: str) -> bytes:
    text = family.encode("utf-16-be")
    return struct.pack(">HHH6H", 0, 1, 18, 3, 1, 0x409, 1, len(text), 0) + text


def cmap_table(ranges: list[tuple[int, int]], kind: int) -> bytes:
    if kind == 12:
        groups = b"".join(struct.pack(">III", a, b, 1) for a, b in ranges)
        body = struct.pack(">HHIII", 12, 0, 16 + len(groups), 0, len(ranges)) + groups
        return struct.pack(">HHHHI", 0, 1, 3, 10, 12) + body
    segments = [*ranges, (0xFFFF, 0xFFFF)]
    count = len(segments)
    ends = struct.pack(f">{count}H", *(b for _a, b in segments))
    starts = struct.pack(f">{count}H", *(a for a, _b in segments))
    zeros = struct.pack(f">{count}H", *([0] * count))
    body = struct.pack(">7H", 4, 0, 0, 2 * count, 0, 0, 0) + ends + b"\0\0" + starts + zeros * 2
    return struct.pack(">HHHHI", 0, 1, 3, 1, 12) + body


def face(family: str, ranges: list[tuple[int, int]], kind: int = 4, base: int = 0) -> bytes:
    """One face whose tables sit right after its directory, at offsets counted from base."""
    cmap, name = cmap_table(ranges, kind), name_table(family)
    first = base + 12 + 2 * 16
    head = struct.pack(">IHHHH", 0x00010000, 2, 0, 0, 0)
    head += struct.pack(">4sIII", b"cmap", 0, first, len(cmap))
    head += struct.pack(">4sIII", b"name", 0, first + len(cmap), len(name))
    return head + cmap + name


def collection(*faces: tuple[str, list[tuple[int, int]]]) -> bytes:
    start = 12 + 4 * len(faces)
    made, offsets = b"", []
    for family, ranges in faces:
        offsets.append(start + len(made))
        made += face(family, ranges, 4, start + len(made))
    count = len(faces)
    return b"ttcf" + struct.pack(f">HHI{count}I", 1, 0, count, *offsets) + made


@pytest.fixture
def fonts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "naskh.ttf").write_bytes(face("Test Naskh", ARABIC))
    (tmp_path / "sans.otf").write_bytes(face("Latin Sans", LATIN, kind=12))
    (tmp_path / "deep").mkdir()
    (tmp_path / "deep" / "pair.TTC").write_bytes(collection(("Pair Arabic", ARABIC + LATIN),
                                                            ("Pair Latin", LATIN)))
    (tmp_path / "dubai.ttf").write_bytes(face("Dubai", ARABIC))
    (tmp_path / "broken.ttf").write_bytes(b"\0\1\0\0 not a font")
    (tmp_path / "notes.txt").write_text("not a font", encoding="utf-8")
    monkeypatch.setattr(font_cover, "folders", lambda: [tmp_path, tmp_path / "missing"])
    return tmp_path


def test_a_font_file_says_its_family_and_the_letters_it_draws(fonts: Path) -> None:
    [(family, ranges)] = read(fonts / "naskh.ttf")
    assert family == "Test Naskh" and covers(ranges, "العربية") and not covers(ranges, "abc")
    assert [f for f, _r in read(fonts / "deep" / "pair.TTC")] == ["Pair Arabic", "Pair Latin"]
    assert read(fonts / "sans.otf")[0][0] == "Latin Sans"
    assert read(fonts / "broken.ttf") == [] and read(fonts / "gone.ttf") == []


def test_only_fonts_that_write_the_language_are_listed_its_own_first(fonts: Path) -> None:
    assert font_cover.covering("ar") == ["Dubai", "Pair Arabic", "Test Naskh"]
    assert font_cover.covering("en") == ["Latin Sans", "Pair Arabic", "Pair Latin"]
    assert font_cover.covering("ja") == []


def test_a_font_is_refused_only_when_it_cannot_write_the_language(fonts: Path,
                                                                  monkeypatch: pytest.MonkeyPatch
                                                                  ) -> None:
    assert font_cover.writes("test naskh", "ar") is None
    assert font_cover.writes("Latin Sans", "ar") == ["Dubai", "Pair Arabic", "Test Naskh"]
    monkeypatch.setattr(font_cover, "folders", lambda: [fonts / "missing"])
    assert font_cover.covering("ar") is None and font_cover.writes("Anything", "ar") is None
