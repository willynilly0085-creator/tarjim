from tarjim.models import Cue, Word
from tarjim.translate.glossary import instructions, parse
from tarjim.translate.prompt import Brief, build_prompt


def test_terms_are_read_one_per_line_or_separated_by_semicolons() -> None:
    assert parse("tarjim = ترجم\nnot a term\n; Pocketflow=بوكِت فلو") == (
        ("tarjim", "ترجم"), ("Pocketflow", "بوكِت فلو"))
    assert parse("") == ()


def test_the_translator_is_told_to_keep_the_terms() -> None:
    cue = Cue(0.0, 2.0, [Word("Meet", 0.0, 0.5), Word("tarjim.", 0.5, 1.0)])
    prompt = build_prompt([cue], Brief(glossary=parse("tarjim = ترجم")))
    assert "tarjim → ترجم" in prompt
    assert instructions(()) == ""


def test_a_language_code_limits_a_term_to_that_language() -> None:
    text = "ar: tarjim = ترجم\nPocketflow = Pocketflow\nja: tarjim = タルジム"
    assert parse(text, "ar") == (("tarjim", "ترجم"), ("Pocketflow", "Pocketflow"))
    assert parse(text, "fr") == (("Pocketflow", "Pocketflow"),)
    assert parse(text, "Japanese") == (("Pocketflow", "Pocketflow"), ("tarjim", "タルジム"))
