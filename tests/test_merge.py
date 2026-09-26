from tarjim.listen.gemini_listen import Utterance
from tarjim.listen.merge import listen_many
from tarjim.listen.vote import vote

A = [Utterance(10.0, 13.0, "S3", "Maybe like once every three months."),
     Utterance(12.1, 13.0, "S1", "Nice."),
     Utterance(17.0, 18.0, "S1", "Nice.")]
B = [Utterance(10.2, 13.2, "S4", "Maybe once every three months"),
     Utterance(17.6, 18.6, "S2", "Nice.")]
C = [Utterance(10.0, 12.0, "S2", "Maybe like once every like three months."),
     Utterance(17.0, 18.0, "S1", "Nice.")]


def test_a_line_heard_by_one_pass_only_is_dropped() -> None:
    kept = vote([A, B, C])
    assert [(u.text, u.start) for u in kept] == [
        ("Maybe like once every three months.", 10.0), ("Nice.", 17.0)]


def test_passes_that_split_sentences_differently_still_agree_word_by_word() -> None:
    fine = [Utterance(53.3, 55.7, "S14", "Probably about once a month."),
            Utterance(55.8, 57.1, "S1", "Longer than that?"),
            Utterance(57.2, 57.8, "S14", "Really?"),
            Utterance(57.9, 60.0, "S1", "And it's gross.")]
    lumped = [Utterance(52.0, 58.0, "S9", "Probably about once a month. Longer than that? "
                                          "Really? And it's gross.")]
    kept = vote([fine, lumped, lumped[:0]])
    assert [u.text for u in kept] == [u.text for u in fine]
    assert kept[2].start == 57.2


def test_a_line_one_pass_missed_is_kept_when_two_others_agree() -> None:
    late = [Utterance(56.0, 57.2, "S1", "And it's gross.")]
    long_intro = [Utterance(0.0, 3.4, "S1", "Okay, I asked everyone how often do they shower.")]
    for runs in ([long_intro + A, C + late, B + late], [A, C + late, B + late]):
        assert vote(runs)[-1].text == "And it's gross."


def test_listen_many_survives_one_failed_pass() -> None:
    calls = iter([RuntimeError("503"), ("English", A)])

    def listen() -> tuple[str, list[Utterance]]:
        outcome = next(calls)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    heard = listen_many(listen, passes=2)
    assert heard.language == "English"
    assert len(heard.utterances) == len(A)
    assert heard.passes == [A]
