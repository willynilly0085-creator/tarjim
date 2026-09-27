# Contributing

Thank you for helping. A few rules keep tarjim easy to read and safe to change.

## Before you open a pull request

```bash
pip install -e ".[dub,dev]"
pytest
ruff check tarjim tests
mypy tarjim
```

All four must pass. The limits are enforced by the configuration in `pyproject.toml`: files under
200 lines, functions under 20 statements with complexity 6 or less, at most 4 arguments, lines under
100 characters, `mypy --strict`.

## How changes are made here

- Write the failing test first, then the code that makes it pass.
- Measure before you claim: timing, quality and speed changes come with the numbers that show them,
  recorded as a dated line in `docs/decisions.md` (append only).
- Names carry the meaning; comments explain only what the code cannot.
- Interface text lives in the language files (`tarjim/web/i18n`, `extension/_locales`), in simple
  Saudi Arabic and English. No emoji in the interface.
- Nothing may send a person's media or keys anywhere they did not choose. Local mode must stay at
  zero external connections.
