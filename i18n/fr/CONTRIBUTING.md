# Contribuer
<!-- languages -->
[English](../../CONTRIBUTING.md) · [العربية](../../i18n/ar/CONTRIBUTING.md) · [Español](../../i18n/es/CONTRIBUTING.md) · **Français** · [Português](../../i18n/pt/CONTRIBUTING.md) · [Deutsch](../../i18n/de/CONTRIBUTING.md) · [Русский](../../i18n/ru/CONTRIBUTING.md) · [Türkçe](../../i18n/tr/CONTRIBUTING.md) · [हिन्दी](../../i18n/hi/CONTRIBUTING.md) · [اردو](../../i18n/ur/CONTRIBUTING.md) · [Bahasa Indonesia](../../i18n/id/CONTRIBUTING.md) · [日本語](../../i18n/ja/CONTRIBUTING.md) · [中文](../../i18n/zh/CONTRIBUTING.md) · [한국어](../../i18n/ko/CONTRIBUTING.md)

Merci de votre aide. Quelques règles permettent à tarjim de rester facile à lire et sûr à modifier.

## Avant d'ouvrir une pull request

```bash
pip install -e ".[dub,dev]"
pytest
ruff check tarjim tests
mypy tarjim
```

Les quatre vérifications doivent réussir. Les limites sont imposées par la configuration de
`pyproject.toml` : fichiers de moins de 200 lignes, fonctions de moins de 20 instructions avec une
complexité de 6 au plus, 4 arguments au maximum, lignes de moins de 100 caractères, `mypy --strict`.

## Comment les modifications se font ici

- Écrivez d'abord le test qui échoue, puis le code qui le fait passer.
- Mesurez avant d'affirmer : toute modification de synchronisation, de qualité ou de vitesse
  s'accompagne des chiffres qui la démontrent, consignés sous forme de ligne datée dans
  `docs/decisions.md` (ajout uniquement).
- Les noms portent le sens ; les commentaires n'expliquent que ce que le code ne peut pas dire.
- Les textes de l'interface se trouvent dans les fichiers de langue (`tarjim/web/i18n`,
  `tarjim/extension/_locales`), en arabe saoudien simple et en anglais. Pas d'emoji dans l'interface.
- Rien ne doit envoyer les médias ou les clés d'une personne vers une destination qu'elle n'a pas
  choisie. Le mode local doit rester à zéro connexion externe.
