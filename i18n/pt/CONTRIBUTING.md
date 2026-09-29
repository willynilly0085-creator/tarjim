# Como contribuir
<!-- languages -->
[English](../../CONTRIBUTING.md) · [العربية](../../i18n/ar/CONTRIBUTING.md) · [Español](../../i18n/es/CONTRIBUTING.md) · [Français](../../i18n/fr/CONTRIBUTING.md) · **Português** · [Deutsch](../../i18n/de/CONTRIBUTING.md) · [Русский](../../i18n/ru/CONTRIBUTING.md) · [Türkçe](../../i18n/tr/CONTRIBUTING.md) · [हिन्दी](../../i18n/hi/CONTRIBUTING.md) · [اردو](../../i18n/ur/CONTRIBUTING.md) · [Bahasa Indonesia](../../i18n/id/CONTRIBUTING.md) · [日本語](../../i18n/ja/CONTRIBUTING.md) · [中文](../../i18n/zh/CONTRIBUTING.md) · [한국어](../../i18n/ko/CONTRIBUTING.md)

Obrigado pela ajuda. Algumas regras mantêm o tarjim fácil de ler e seguro de modificar.

## Antes de abrir um pull request

```bash
pip install -e ".[dub,dev]"
pytest
ruff check tarjim tests
mypy tarjim
```

As quatro verificações precisam passar. Os limites são garantidos pela configuração em
`pyproject.toml`: arquivos com menos de 200 linhas, funções com menos de 20 instruções e
complexidade 6 ou menor, no máximo 4 argumentos, linhas com menos de 100 caracteres, `mypy --strict`.

## Como as mudanças são feitas aqui

- Escreva primeiro o teste que falha, depois o código que o faz passar.
- Meça antes de afirmar: mudanças de sincronização, qualidade e velocidade vêm acompanhadas dos
  números que as comprovam, registrados como uma linha datada em `docs/decisions.md` (só se
  acrescentam linhas).
- Os nomes carregam o significado; os comentários explicam apenas o que o código não consegue.
- Os textos da interface ficam nos arquivos de idioma (`tarjim/web/i18n`, `tarjim/extension/_locales`), em
  árabe saudita simples e em inglês. Nada de emoji na interface.
- Nada pode enviar a mídia ou as chaves de uma pessoa para qualquer lugar que ela não tenha
  escolhido. O modo local deve continuar com zero conexões externas.
