from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import listen_many, merge

A = [Utterance(55.8, 57.1, "S1", "Longer than that."),
     Utterance(53.3, 55.7, "S14", "Probably.")]
B = [Utterance(55.9, 57.0, "S2", "Longer than that"),
     Utterance(57.9, 60.0, "S1", "And it's gross.")]


def test_merge_adds_only_turns_the_primary_missed() -> None:
    merged = merge(A, B, tag="p2.")
    assert [u.text for u in merged] == ["Probably.", "Longer than that.", "And it's gross."]
    assert merged[-1].speaker == "p2.S1"


def test_listen_many_survives_one_failed_pass() -> None:
    calls = iter([RuntimeError("503"), ("English", A)])

    def listen() -> tuple[str, list[Utterance]]:
        outcome = next(calls)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    language, merged = listen_many(listen)
    assert language == "English"
    assert len(merged) == len(A)
