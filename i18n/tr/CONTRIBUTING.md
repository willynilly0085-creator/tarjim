# Katkıda bulunma
<!-- languages -->
[English](../../CONTRIBUTING.md) · [العربية](../../i18n/ar/CONTRIBUTING.md) · [Español](../../i18n/es/CONTRIBUTING.md) · [Français](../../i18n/fr/CONTRIBUTING.md) · [Português](../../i18n/pt/CONTRIBUTING.md) · [Deutsch](../../i18n/de/CONTRIBUTING.md) · [Русский](../../i18n/ru/CONTRIBUTING.md) · **Türkçe** · [हिन्दी](../../i18n/hi/CONTRIBUTING.md) · [اردو](../../i18n/ur/CONTRIBUTING.md) · [Bahasa Indonesia](../../i18n/id/CONTRIBUTING.md) · [日本語](../../i18n/ja/CONTRIBUTING.md) · [中文](../../i18n/zh/CONTRIBUTING.md) · [한국어](../../i18n/ko/CONTRIBUTING.md)

Yardımınız için teşekkürler. Birkaç kural, tarjim'in kolay okunmasını ve güvenle
değiştirilebilmesini sağlar.

## Bir pull request açmadan önce

```bash
pip install -e ".[dub,dev]"
pytest
ruff check tarjim tests
mypy tarjim
```

Dördünün de başarılı olması gerekir. Sınırlar `pyproject.toml` içindeki yapılandırmayla uygulanır:
dosyalar 200 satırın altında, fonksiyonlar 20 ifadenin altında ve karmaşıklığı en fazla 6, en fazla
4 argüman, satırlar 100 karakterin altında, `mypy --strict`.

## Burada değişiklikler nasıl yapılır

- Önce başarısız olan testi, ardından onu geçiren kodu yazın.
- İddia etmeden önce ölçün: zamanlama, kalite ve hız değişiklikleri, bunları gösteren sayılarla
  birlikte gelir ve `docs/decisions.md` dosyasına tarihli bir satır olarak kaydedilir (yalnızca
  ekleme yapılır).
- Anlamı adlar taşır; yorumlar yalnızca kodun anlatamadığını açıklar.
- Arayüz metinleri dil dosyalarında (`tarjim/web/i18n`, `tarjim/extension/_locales`), sade Suudi Arapçası
  ve İngilizce olarak bulunur. Arayüzde emoji kullanılmaz.
- Hiçbir şey bir kişinin medyasını veya anahtarlarını onun seçmediği bir yere gönderemez. Yerel mod
  sıfır dış bağlantıda kalmalıdır.
