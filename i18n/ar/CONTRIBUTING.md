# المساهمة
<!-- languages -->
[English](../../CONTRIBUTING.md) · **العربية** · [Español](../../i18n/es/CONTRIBUTING.md) · [Français](../../i18n/fr/CONTRIBUTING.md) · [Português](../../i18n/pt/CONTRIBUTING.md) · [Deutsch](../../i18n/de/CONTRIBUTING.md) · [Русский](../../i18n/ru/CONTRIBUTING.md) · [Türkçe](../../i18n/tr/CONTRIBUTING.md) · [हिन्दी](../../i18n/hi/CONTRIBUTING.md) · [اردو](../../i18n/ur/CONTRIBUTING.md) · [Bahasa Indonesia](../../i18n/id/CONTRIBUTING.md) · [日本語](../../i18n/ja/CONTRIBUTING.md) · [中文](../../i18n/zh/CONTRIBUTING.md) · [한국어](../../i18n/ko/CONTRIBUTING.md)

شكراً على مساعدتك. فيه قواعد بسيطة تخلي ترجم سهل القراءة وآمن للتعديل.

## قبل ما تفتح طلب دمج (pull request)

```bash
pip install -e ".[dub,dev]"
pytest
ruff check tarjim tests
mypy tarjim
```

الأربعة لازم تنجح. الحدود مفروضة من الإعدادات في `pyproject.toml`: الملفات أقل من 200 سطر، والدوال
أقل من 20 تعليمة وتعقيدها 6 أو أقل، وبحد أقصى 4 وسائط، والأسطر أقل من 100 حرف، و `mypy --strict`.

## كيف تنعمل التغييرات هنا

- اكتب الاختبار اللي يفشل أول، وبعدها الكود اللي يخليه ينجح.
- قِس قبل ما تدّعي: أي تغيير في التوقيت أو الجودة أو السرعة يجي معه الأرقام اللي تثبته، مسجّلة كسطر
  مؤرّخ في `docs/decisions.md` (إضافة فقط، بدون تعديل اللي قبله).
- الأسماء هي اللي توضح المعنى، والتعليقات تشرح بس اللي الكود ما يقدر يوضحه.
- نصوص الواجهة موجودة في ملفات اللغات (`tarjim/web/i18n`، `extension/_locales`)، بعربي سعودي بسيط
  وإنجليزي. ممنوع الإيموجي في الواجهة.
- ولا شي يرسل وسائط الشخص أو مفاتيحه لأي مكان ما اختاره هو. والوضع المحلي لازم يبقى على صفر اتصالات
  خارجية.
