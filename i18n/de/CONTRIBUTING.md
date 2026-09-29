# Mitwirken
<!-- languages -->
[English](../../CONTRIBUTING.md) · [العربية](../../i18n/ar/CONTRIBUTING.md) · [Español](../../i18n/es/CONTRIBUTING.md) · [Français](../../i18n/fr/CONTRIBUTING.md) · [Português](../../i18n/pt/CONTRIBUTING.md) · **Deutsch** · [Русский](../../i18n/ru/CONTRIBUTING.md) · [Türkçe](../../i18n/tr/CONTRIBUTING.md) · [हिन्दी](../../i18n/hi/CONTRIBUTING.md) · [اردو](../../i18n/ur/CONTRIBUTING.md) · [Bahasa Indonesia](../../i18n/id/CONTRIBUTING.md) · [日本語](../../i18n/ja/CONTRIBUTING.md) · [中文](../../i18n/zh/CONTRIBUTING.md) · [한국어](../../i18n/ko/CONTRIBUTING.md)

Danke für Ihre Hilfe. Ein paar Regeln sorgen dafür, dass tarjim gut lesbar bleibt und sich sicher
ändern lässt.

## Bevor Sie einen Pull Request öffnen

```bash
pip install -e ".[dub,dev]"
pytest
ruff check tarjim tests
mypy tarjim
```

Alle vier müssen erfolgreich durchlaufen. Die Grenzen werden durch die Konfiguration in
`pyproject.toml` durchgesetzt: Dateien unter 200 Zeilen, Funktionen unter 20 Anweisungen mit einer
Komplexität von höchstens 6, höchstens 4 Argumente, Zeilen unter 100 Zeichen, `mypy --strict`.

## Wie hier Änderungen entstehen

- Schreiben Sie zuerst den fehlschlagenden Test, dann den Code, der ihn bestehen lässt.
- Erst messen, dann behaupten: Änderungen an Timing, Qualität und Geschwindigkeit kommen mit den
  Zahlen, die sie belegen, festgehalten als datierte Zeile in `docs/decisions.md` (nur anhängen).
- Namen tragen die Bedeutung; Kommentare erklären nur, was der Code selbst nicht ausdrücken kann.
- Oberflächentexte stehen in den Sprachdateien (`tarjim/web/i18n`, `tarjim/extension/_locales`), in
  einfachem saudischem Arabisch und in Englisch. Keine Emojis in der Oberfläche.
- Nichts darf die Medien oder Schlüssel einer Person an einen Ort senden, den sie nicht gewählt hat.
  Der lokale Modus muss bei null externen Verbindungen bleiben.
