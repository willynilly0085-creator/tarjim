"""The project's size limit read off the files themselves (2026-11-08): ruff and mypy do not
count lines, so a module over 200 lines passed every gate; the tolerant decoder's own cap is
190."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "tarjim"
LIMIT = 200
CAPS = {"asr/tolerant.py": 190}


def lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def test_no_module_is_over_the_line_limit() -> None:
    over = {str(p.relative_to(ROOT)): n for p in ROOT.rglob("*.py") if (n := lines(p)) > LIMIT}
    assert over == {}


def test_the_tolerant_decoder_keeps_its_own_cap() -> None:
    for name, cap in CAPS.items():
        assert lines(ROOT / name) <= cap, name
