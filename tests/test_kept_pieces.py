"""A kept hearing is voted again the way it was first heard (2026-11-08): piece by piece for a long
clip, as it was stored for a hearing kept before pieces were, and a pass the sanity check emptied
takes no part in the vote."""
import json
from pathlib import Path

from tarjim.listen.chunks import listen_in_chunks
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.kept import keep_heard, load_heard
from tarjim.listen.merge import Heard, agreed, spoken


def words(prefix: str, count: int) -> str:
    return " ".join(f"{prefix}{k}" for k in range(count))


def lines(offset: float = 0.0, tag: str = "w") -> list[Utterance]:
    return [Utterance(6.0 * k + offset, 6.0 * k + offset + 5.0, "S1", words(f"{tag}{k}x", 5))
            for k in range(10)]


BROKEN = Utterance(0.0, 129.0, "S1", words("long", 60))  # the whole speech in one line


def test_a_pass_the_sanity_check_emptied_does_not_empty_the_vote() -> None:
    first, second = lines(), lines(10.0)  # the same words 10 s apart: the vote keeps none
    assert spoken(agreed([first, second])) == 50
    assert spoken(agreed([first, second, [BROKEN]])) == 50


REPLY = Utterance(62.0, 63.5, "S2", "yes indeed my friend")


def piece_heard(start: float, _end: float) -> Heard:
    """Piece one: two of three passes hear a reply. Piece two: its longest pass also holds one
    broken line, more than a tenth of a whole clip's pass once the pieces are joined."""
    if start == 0.0:
        runs = [[*lines(), REPLY], [*lines(), REPLY], lines()]
    else:
        long = Utterance(0.0, 61.0, "S1", words("long", 60))
        runs = [[*lines(), long], lines(), lines()]
    return Heard("English", agreed(runs), runs)


def test_a_long_clip_kept_and_loaded_is_voted_as_it_was_heard(tmp_path: Path) -> None:
    fresh = listen_in_chunks(150.0, [], piece_heard, target=75.0)
    assert REPLY.text in {u.text for u in fresh.utterances}
    keep_heard(tmp_path, fresh)
    loaded = load_heard(tmp_path)
    assert loaded is not None and loaded.utterances == fresh.utterances
    assert loaded.passes == fresh.passes and loaded.pieces == fresh.pieces


def test_a_hearing_kept_before_pieces_uses_its_stored_lines(tmp_path: Path) -> None:
    stored = [Utterance(1.0, 2.0, "S1", "as it was voted")]
    passes = [[*lines(), REPLY], lines(), lines()]
    data = {"language": "English", "utterances": [vars(u) for u in stored],
            "passes": [[vars(u) for u in run] for run in passes], "provider": "gemini"}
    (tmp_path / "heard.json").write_text(json.dumps(data), encoding="utf-8")
    loaded = load_heard(tmp_path)
    assert loaded is not None and loaded.utterances == stored and len(loaded.passes) == 3
