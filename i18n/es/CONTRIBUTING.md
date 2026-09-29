# Cómo contribuir
<!-- languages -->
[English](../../CONTRIBUTING.md) · [العربية](../../i18n/ar/CONTRIBUTING.md) · **Español** · [Français](../../i18n/fr/CONTRIBUTING.md) · [Português](../../i18n/pt/CONTRIBUTING.md) · [Deutsch](../../i18n/de/CONTRIBUTING.md) · [Русский](../../i18n/ru/CONTRIBUTING.md) · [Türkçe](../../i18n/tr/CONTRIBUTING.md) · [हिन्दी](../../i18n/hi/CONTRIBUTING.md) · [اردو](../../i18n/ur/CONTRIBUTING.md) · [Bahasa Indonesia](../../i18n/id/CONTRIBUTING.md) · [日本語](../../i18n/ja/CONTRIBUTING.md) · [中文](../../i18n/zh/CONTRIBUTING.md) · [한국어](../../i18n/ko/CONTRIBUTING.md)

Gracias por tu ayuda. Unas pocas reglas mantienen tarjim fácil de leer y seguro de modificar.

## Antes de abrir una pull request

```bash
pip install -e ".[dub,dev]"
pytest
ruff check tarjim tests
mypy tarjim
```

Las cuatro comprobaciones deben pasar. Los límites los impone la configuración de `pyproject.toml`:
archivos de menos de 200 líneas, funciones de menos de 20 sentencias con una complejidad de 6 o
menos, un máximo de 4 argumentos, líneas de menos de 100 caracteres, `mypy --strict`.

## Cómo se hacen los cambios aquí

- Escribe primero la prueba que falla y después el código que la hace pasar.
- Mide antes de afirmar: los cambios de sincronización, calidad y velocidad van acompañados de las
  cifras que los demuestran, registradas como una línea con fecha en `docs/decisions.md` (solo se
  añaden líneas).
- Los nombres transmiten el significado; los comentarios explican solo lo que el código no puede.
- Los textos de la interfaz viven en los archivos de idioma (`tarjim/web/i18n`, `tarjim/extension/_locales`),
  en árabe saudí sencillo y en inglés. Nada de emojis en la interfaz.
- Nada puede enviar los archivos multimedia o las claves de una persona a ningún sitio que no haya
  elegido. El modo local debe mantenerse en cero conexiones externas.
