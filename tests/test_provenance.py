"""Every line carries where it came from and every word how it got its time (2026-11-08): the
piece a line was heard in, the request that heard it and how far its time is trusted; a word's
source (aligned, heard, estimated, unplaced) and score. A missed constructor would silently say
"unknown", so every `Word(` and `Utterance(` in tarjim is checked here."""
import ast
import json
from pathlib import Path

from tarjim.listen.chunks import joined, listen_in_chunks
from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.kept import keep_heard, keep_transcript, kept_transcript, load_heard
from tarjim.listen.lead import LINK_LEAD
from tarjim.listen.merge import Heard, Piece
from tarjim.listen.vote import vote
from tarjim.models import SOURCES, Word

ROOT = Path(__file__).resolve().parent.parent / "tarjim"
# rebuilt from what a listener answered or a file kept, or a dub's own text
PLAIN = {("listen/gemini_listen.py", "parse"), ("dub/split.py", "word_times")}


def calls(name: str) -> list[tuple[str, str, ast.Call]]:
    found = []
    for path in sorted(ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        where = path.relative_to(ROOT).as_posix()
        for function in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            found += [(where, function.name, n) for n in ast.walk(function)
                      if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                      and n.func.id == name]
    return found


def given(call: ast.Call, field: str) -> bool:
    return any(k.arg in (field, None) for k in call.keywords)  # None: a loader's **row


def test_every_word_made_in_tarjim_says_its_source() -> None:
    found = calls("Word")
    assert found
    assert [(w, f, c.lineno) for w, f, c in found if not given(c, "source")] == []


def test_every_new_line_in_tarjim_says_its_request() -> None:
    found = [(w, f, c.lineno) for w, f, c in calls("Utterance")
             if (w, f) not in PLAIN and not given(c, "request")]
    assert found == []


def test_the_new_fields_leave_equality_alone() -> None:
    assert Word("a", 1.0, 2.0, "S1", score=0.5, source="aligned") == Word("a", 1.0, 2.0, "S1")
    assert len({Word("a", 1.0, 2.0), Word("a", 1.0, 2.0, source="heard")}) == 1
    line = Utterance(1.0, 2.0, "S1", "hi", piece=(0.0, 75.0), request="k0.v", prior=0.0)
    assert line == Utterance(1.0, 2.0, "S1", "hi")
    assert set(SOURCES) >= {"aligned", "heard", "estimated", "unplaced", "unknown"}


def test_a_hearing_kept_before_the_fields_still_loads(tmp_path: Path) -> None:
    rows = [{"start": 1.0, "end": 2.0, "speaker": "S1", "text": "old line"}]
    piece = {"start": 0.0, "end": 75.0, "passes": [rows, rows, rows]}
    data = {"language": "English", "utterances": rows, "passes": [rows], "pieces": [piece],
            "added": [{"line": rows[0], "gap": [1.0, 2.0]}]}
    (tmp_path / "heard.json").write_text(json.dumps(data), encoding="utf-8")
    loaded = load_heard(tmp_path)
    assert loaded is not None and loaded.utterances[0].text == "old line"
    assert loaded.utterances[0].piece == (0.0, 75.0) and loaded.utterances[0].request == "k0.v"
    assert loaded.added[0].line.request == "" and loaded.added[0].line.prior == 1.0
    assert loaded.pieces[0].language == ""


def test_a_transcript_kept_before_the_fields_still_loads(tmp_path: Path) -> None:
    data = {"language": "English", "text": "hi", "words": [
        {"text": "hi", "start": 1.0, "end": 1.2, "speaker": "S1"}]}
    (tmp_path / "transcript.json").write_text(json.dumps(data), encoding="utf-8")
    found = kept_transcript(tmp_path)
    assert found is not None and found[0].words[0].source == "unknown"
    assert found[0].words[0].score is None


def test_a_transcript_keeps_its_words_sources(tmp_path: Path) -> None:
    from tarjim.asr.base import Transcript

    words = [Word("hi", 1.0, 1.2, "S1", score=-0.4, source="aligned")]
    keep_transcript(tmp_path, Transcript(language="English", text="hi", words=words))
    found = kept_transcript(tmp_path)
    assert found is not None and found[0].words[0].source == "aligned"
    assert found[0].words[0].score == -0.4


def heard_in(start: float, _end: float) -> Heard:
    lead = LINK_LEAD if start else 0.0  # heard before the piece itself (2026-11-09)
    run = [Utterance(lead + 2.0, lead + 4.0, "S1", f"said at {start + lead:.0f} seconds"),
           Utterance(lead + 5.0, lead + 7.0, "S2", "and an answer to it")]
    return Heard("French" if start else "English", run, [run, run, run])


def test_lines_carry_their_piece_and_request_and_a_reload_gives_the_same(
        tmp_path: Path) -> None:
    fresh = listen_in_chunks(200.0, [], heard_in, target=100.0)
    assert [u.piece for u in fresh.utterances] == [(0.0, 100.0)] * 2 + [(100.0, 200.0)] * 2
    assert [u.request for u in fresh.utterances] == ["k0.v", "k0.v", "k1.v", "k1.v"]
    assert [u.request for u in fresh.passes[2]] == ["k0.p2", "k0.p2", "k1.p2", "k1.p2"]
    assert [p.language for p in fresh.pieces] == ["English", "French"]
    assert fresh.language == "English"
    keep_heard(tmp_path, fresh)
    loaded = load_heard(tmp_path)
    assert loaded is not None
    assert [(u.piece, u.request, u.prior) for u in loaded.utterances] == \
        [(u.piece, u.request, u.prior) for u in fresh.utterances]
    assert [p.language for p in loaded.pieces] == ["English", "French"]


def test_the_vote_keeps_the_base_lines_provenance() -> None:
    base = [Utterance(1.0, 3.0, "S1", "one two three four", piece=(0.0, 9.0), request="r1"),
            Utterance(4.0, 5.0, "S2", "a reply only two heard", request="r1")]
    other = [Utterance(1.2, 3.1, "S1", "one two three four", request="r2")]
    voted = vote([base, other, list(base)])
    assert [(u.piece, u.request) for u in voted] == [((0.0, 9.0), "r1"), (None, "r1")]


def test_joined_pieces_give_every_line_its_piece() -> None:
    line = Utterance(1.0, 2.0, "S1", "hello there")
    lines, passes = joined([Piece(10.0, 20.0, [[line], [line]], "English")])
    assert lines[0].piece == (10.0, 20.0) and lines[0].start == 11.0
    assert [u.request for run in passes for u in run] == ["k0.p0", "k0.p1"]
