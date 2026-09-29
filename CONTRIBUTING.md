# Contributing
<!-- languages -->
**English** · [العربية](i18n/ar/CONTRIBUTING.md) · [Español](i18n/es/CONTRIBUTING.md) · [Français](i18n/fr/CONTRIBUTING.md) · [Português](i18n/pt/CONTRIBUTING.md) · [Deutsch](i18n/de/CONTRIBUTING.md) · [Русский](i18n/ru/CONTRIBUTING.md) · [Türkçe](i18n/tr/CONTRIBUTING.md) · [हिन्दी](i18n/hi/CONTRIBUTING.md) · [اردو](i18n/ur/CONTRIBUTING.md) · [Bahasa Indonesia](i18n/id/CONTRIBUTING.md) · [日本語](i18n/ja/CONTRIBUTING.md) · [中文](i18n/zh/CONTRIBUTING.md) · [한국어](i18n/ko/CONTRIBUTING.md)

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
- Interface text lives in the language files (`tarjim/web/i18n`, `tarjim/extension/_locales`), in simple
  Saudi Arabic and English. No emoji in the interface.
- Nothing may send a person's media or keys anywhere they did not choose. Local mode must stay at
  zero external connections.
