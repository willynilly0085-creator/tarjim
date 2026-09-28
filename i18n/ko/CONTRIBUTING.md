# 기여하기
<!-- languages -->
[English](../../CONTRIBUTING.md) · [العربية](../../i18n/ar/CONTRIBUTING.md) · [Español](../../i18n/es/CONTRIBUTING.md) · [Français](../../i18n/fr/CONTRIBUTING.md) · [Português](../../i18n/pt/CONTRIBUTING.md) · [Deutsch](../../i18n/de/CONTRIBUTING.md) · [Русский](../../i18n/ru/CONTRIBUTING.md) · [Türkçe](../../i18n/tr/CONTRIBUTING.md) · [हिन्दी](../../i18n/hi/CONTRIBUTING.md) · [اردو](../../i18n/ur/CONTRIBUTING.md) · [Bahasa Indonesia](../../i18n/id/CONTRIBUTING.md) · [日本語](../../i18n/ja/CONTRIBUTING.md) · [中文](../../i18n/zh/CONTRIBUTING.md) · **한국어**

도와주셔서 감사합니다. tarjim을 읽기 쉽고 안전하게 수정할 수 있도록 몇 가지 규칙을 지켜 주세요.

## 풀 리퀘스트를 열기 전에

```bash
pip install -e ".[dub,dev]"
pytest
ruff check tarjim tests
mypy tarjim
```

네 가지 모두 통과해야 합니다. 제한 사항은 `pyproject.toml`의 설정으로 강제됩니다. 파일은 200줄 미만, 함수는 20개 문 미만에 복잡도 6 이하, 인자는 최대 4개, 한 줄은 100자 미만이어야 하며 `mypy --strict`를 통과해야 합니다.

## 이 프로젝트에서 변경하는 방식

- 먼저 실패하는 테스트를 작성하고, 그다음 그 테스트를 통과시키는 코드를 작성합니다.
- 주장하기 전에 측정합니다. 타이밍, 품질, 속도에 관한 변경에는 이를 뒷받침하는 수치를 함께 제시하고, `docs/decisions.md`에 날짜가 적힌 한 줄로 기록합니다(추가만 가능).
- 의미는 이름으로 드러냅니다. 주석은 코드로 표현할 수 없는 것만 설명합니다.
- 인터페이스 문구는 언어 파일(`tarjim/web/i18n`, `extension/_locales`)에 두며, 쉬운 사우디 아랍어와 영어로 작성합니다. 인터페이스에는 이모지를 쓰지 않습니다.
- 어떤 기능도 사용자가 선택하지 않은 곳으로 그 사람의 미디어나 키를 보내서는 안 됩니다. 로컬 모드는 외부 연결 0건을 유지해야 합니다.
