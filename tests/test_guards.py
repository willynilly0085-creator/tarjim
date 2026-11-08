"""Each layer that makes up for another one counts its fires per job (tarjim/guards.py,
2026-11-08), so the bench can tell which still matter; the counts change nothing the job does."""
import ast
import threading
from pathlib import Path

import pytest

from tarjim import guards
from tarjim.asr.base import Transcript
from tarjim.findings import collecting
from tarjim.listen.gemini_listen import Utterance
from tarjim.models import Word

U = Utterance
ROOT = Path(guards.__file__).resolve().parent


def count(name: str) -> int:
    return guards.counts()[name]


@pytest.fixture(autouse=True)
def fresh() -> None:
    guards.reset()


def test_every_guard_is_counted_with_zero_when_it_never_fired() -> None:
    found = guards.counts()
    assert list(found) == list(guards.NAMES) and not any(found.values())
    assert guards.said(found) == "guards: none fired"


def test_a_new_job_starts_from_nothing() -> None:
    guards.fired("anchor.moved", 2)
    assert count("anchor.moved") == 2
    assert guards.said(guards.counts()) == "guards: anchor.moved=2"
    collecting()
    assert count("anchor.moved") == 0


def test_two_jobs_in_threads_count_apart() -> None:
    seen: dict[str, int] = {}
    ready = threading.Barrier(2)

    def job(name: str, times: int) -> None:
        guards.reset()
        ready.wait()
        for _ in range(times):
            guards.fired(name)
        ready.wait()
        seen[name] = sum(guards.counts().values())

    threads = [threading.Thread(target=job, args=("fuse.retimed", 3)),
               threading.Thread(target=job, args=("anchor.moved", 5))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert seen == {"fuse.retimed": 3, "anchor.moved": 5}


def named_in_code() -> set[str]:
    found: set[str] = set()
    for path in ROOT.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(
                    node.func, "attr", "")) in ("fired", "when") and node.args and isinstance(
                    node.args[0], ast.Constant) and path.name != "guards.py":
                found.add(str(node.args[0].value))
    return found


def test_every_guard_named_in_the_code_is_listed_and_each_listed_one_is_used() -> None:
    assert named_in_code() == set(guards.NAMES)


def test_the_counts_are_logged_once_and_kept_on_the_findings(
        capsys: pytest.CaptureFixture[str]) -> None:
    found = collecting()
    guards.fired("vote.extras")
    found.guarded()
    assert capsys.readouterr().out == "guards: vote.extras=1\n"
    assert found.guards["vote.extras"] == 1 and found.guards["anchor.moved"] == 0


def test_the_vote_and_the_passes_count_what_they_make_up_for() -> None:
    from tarjim.listen.merge import sane, settled
    from tarjim.listen.vote import vote

    speech = [U(k * 4.0, k * 4.0 + 3.5, "S1", f"line {k} has five words") for k in range(30)]
    sane([*speech, U(130.0, 200.0, "S1", "a line seventy seconds long")])
    sane([U(0.0, 129.1, "S1", " ".join(f"word{k}" for k in range(300)))])
    assert (count("merge.sane_line"), count("merge.sane_pass")) == (1, 1)
    said = "a b c d e f g h i j"
    settled([], [[U(0.0, 3.0, "S1", said)], [U(9.0, 12.0, "S1", said)]])
    assert count("merge.fullest") == 1
    late = [U(56.0, 57.2, "S1", "And it's gross.")]
    vote([[U(0.0, 3.4, "S1", "Okay, I asked everyone how often do they shower.")], late, late])
    assert count("vote.extras") == 1


def test_an_extra_dropped_as_a_copy_is_counted() -> None:
    from tarjim.listen.vote import vote

    base = [U(0.0, 3.0, "S1", "hello there friends and welcome back to the show"),
            U(30.0, 32.0, "S1", "today we cook rice"),
            U(60.0, 62.0, "S1", "hello there friends and welcome back")]
    again = [U(60.0, 63.0, "S1", "hello there friends and welcome back to the show")]
    middle = [U(30.1, 32.1, "S1", "today we cook rice"),
              U(60.1, 62.1, "S1", "hello there friends and welcome back")]
    vote([base, again, middle, again], agree=2)
    assert count("vote.extra_dropped") >= 1


def test_the_hearing_chosen_over_the_vote_is_counted() -> None:
    from tarjim.listen.recover import best_heard

    intro, speech = "please welcome to the stage our guest", "hello atlanta it is good to be back"
    full = [U(30.0, 40.0, "S1", intro), U(92.0, 110.0, "S2", speech)]
    short = [U(30.0, 40.0, "S1", intro)]
    heard = [Word(w, 30.0 + k * 0.4, 30.3 + k * 0.4) for k, w in enumerate(intro.split())] + [
        Word(w, 92.0 + k * 0.4, 92.3 + k * 0.4) for k, w in enumerate(speech.split())]
    assert best_heard(short, [full, short, short], heard) == full
    assert count("recover.not_vote") == 1
    passes = [[U(0.0, 9.0, "S1", speech)], [U(0.0, 6.0, "S1", "hello atlanta it is")]]
    best_heard([U(0.0, 2.0, "S1", "there")], passes, [])
    assert count("recover.fuller") == 1


def timed(agreement: float) -> "object":
    from tarjim.listen.settle import Timed

    return Timed(Transcript("English", "x", []), True, agreement)


def test_the_second_timing_and_the_trusted_words_are_counted() -> None:
    from tarjim.listen.settle import better, trusted

    first, other = timed(0.2), timed(0.9)
    assert better(first, lambda: other, True) is other  # type: ignore[arg-type,return-value]
    assert (count("settle.second_timing"), count("settle.alone_won")) == (1, 1)
    squeezed = [Word(f"w{k}", 65.6 + k * 0.01, 65.605 + k * 0.01) for k in range(40)]
    spoken = [Word(f"w{k}", k * 0.4, k * 0.4 + 0.3) for k in range(40)]
    assert trusted(squeezed, spoken) == spoken
    assert count("settle.trusted") == 1 and count("sanity.implausible") == 1


def test_quiet_counts_nothing_and_counting_resumes_after() -> None:
    with guards.quiet():
        guards.fired("vote.extras", 3)
        assert not guards.when("merge.fullest", False) and guards.when("merge.fullest", True)
    guards.fired("vote.extras")
    assert (count("vote.extras"), count("merge.fullest")) == (1, 0)


def test_one_broken_line_counts_once_fresh_and_kept_alike(tmp_path: Path) -> None:
    """Each decision counts once: a piece's passes voted in listen_many are voted again in
    chunks.joined, and recover.cleaned cleans the passes joined already cleaned (2026-11-08:
    one broken line counted three times fresh and twice kept)."""
    from tarjim.listen.chunks import listen_in_chunks
    from tarjim.listen.kept import keep_heard, load_heard
    from tarjim.listen.merge import listen_many
    from tarjim.listen.recover import best_heard

    good = [U(10.0, 60.0, "S1", " ".join(["talk"] * 300))]
    runs = iter([[*good, U(61.0, 61.1, "S1", " ".join(["word"] * 20))], good, good])
    lock = threading.Lock()

    def listen() -> tuple[str, list[Utterance]]:
        with lock:
            return "English", list(next(runs))

    heard = listen_in_chunks(70.0, [], lambda _s, _e: listen_many(listen), 75.0)
    best_heard(heard.utterances, heard.passes, [])
    fresh = count("merge.sane_line"), count("vote.extras")
    keep_heard(tmp_path, heard)
    guards.reset()
    kept = load_heard(tmp_path)
    assert kept is not None
    best_heard(kept.utterances, kept.passes, [])
    assert fresh == (count("merge.sane_line"), count("vote.extras")) and fresh[0] == 1
