"""What a font file holds, read without a font library (2026-11-09): each face's family name
and the letters it draws. Only the two tables needed (name, cmap) are read, from TrueType,
OpenType and collection (.ttc) files. A file that cannot be read gives nothing, never an error:
the page then lists the fonts that could be read.
"""
import struct
from pathlib import Path
from typing import BinaryIO

Ranges = tuple[tuple[int, int], ...]
Face = tuple[str, Ranges]
COLLECTION = b"ttcf"
MOST_FACES = 64
LARGEST_TABLE = 16 * 1024 * 1024
WINDOWS, ENGLISH_US, FAMILY = 3, 0x409, 1
SEGMENTS, GROUPS = 4, 12  # the cmap formats that cover the Basic Plane and every plane
LAST_CODE = 0xFFFF  # format 4's closing segment, not a letter


def at(source: BinaryIO, offset: int, size: int) -> bytes:
    if not 0 <= size <= LARGEST_TABLE:
        raise ValueError("table too large")
    source.seek(offset)
    data = source.read(size)
    if len(data) != size:
        raise ValueError("font file cut short")
    return data


def faces(source: BinaryIO) -> list[int]:
    """Where each face of the file starts: one, or each of a collection's."""
    head = at(source, 0, 12)
    if head[:4] != COLLECTION:
        return [0]
    count = min(struct.unpack(">I", head[8:12])[0], MOST_FACES)
    return list(struct.unpack(f">{count}I", at(source, 12, 4 * count)))


def tables(source: BinaryIO, offset: int) -> dict[bytes, tuple[int, int]]:
    count = struct.unpack(">H", at(source, offset + 4, 2))[0]
    raw = at(source, offset + 12, 16 * count)
    found = {}
    for i in range(count):
        tag, _sum, start, length = struct.unpack(">4sIII", raw[16 * i:16 * i + 16])
        found[tag] = (start, length)
    return found


def family(data: bytes) -> str:
    """The family name as Windows lists it, in US English when the font has it."""
    count, strings = struct.unpack(">2xHH", data[:6])
    best = ""
    for i in range(count):
        platform, _code, lang, name_id, length, start = struct.unpack(
            ">6H", data[6 + 12 * i:18 + 12 * i])
        if platform != WINDOWS or name_id != FAMILY:
            continue
        text = data[strings + start:strings + start + length].decode("utf-16-be", "replace")
        if lang == ENGLISH_US:
            return text.strip()
        best = best or text.strip()
    return best


def segments(data: bytes, start: int) -> Ranges:
    doubled = struct.unpack(">H", data[start + 6:start + 8])[0]
    count = doubled // 2
    ends = struct.unpack(f">{count}H", data[start + 14:start + 14 + doubled])
    firsts = struct.unpack(f">{count}H", data[start + 16 + doubled:start + 16 + 2 * doubled])
    return tuple((a, b) for a, b in zip(firsts, ends, strict=True) if a != LAST_CODE)


def groups(data: bytes, start: int) -> Ranges:
    count = struct.unpack(">I", data[start + 12:start + 16])[0]
    raw = data[start + 16:start + 16 + 12 * count]
    return tuple((a, b) for a, b, _glyph in struct.iter_unpack(">III", raw))


def letters(data: bytes) -> Ranges:
    """The code points the font maps, from its widest Unicode subtable."""
    count = struct.unpack(">H", data[2:4])[0]
    found: dict[int, Ranges] = {}
    for i in range(count):
        start = struct.unpack(">I", data[8 + 8 * i:12 + 8 * i])[0]
        kind = struct.unpack(">H", data[start:start + 2])[0]
        if kind in (SEGMENTS, GROUPS) and kind not in found:
            found[kind] = (segments if kind == SEGMENTS else groups)(data, start)
    return found.get(GROUPS) or found.get(SEGMENTS) or ()


def face(source: BinaryIO, offset: int) -> Face | None:
    found = tables(source, offset)
    if b"cmap" not in found or b"name" not in found:
        return None
    return family(at(source, *found[b"name"])), letters(at(source, *found[b"cmap"]))


def read(path: Path) -> list[Face]:
    try:
        with path.open("rb") as source:
            return [f for offset in faces(source) if (f := face(source, offset)) is not None]
    except (OSError, ValueError, struct.error):
        return []


def covers(ranges: Ranges, text: str) -> bool:
    return all(any(low <= ord(c) <= high for low, high in ranges) for c in text)
