# Güvenlik
<!-- languages -->
[English](../../SECURITY.md) · [العربية](../../i18n/ar/SECURITY.md) · [Español](../../i18n/es/SECURITY.md) · [Français](../../i18n/fr/SECURITY.md) · [Português](../../i18n/pt/SECURITY.md) · [Deutsch](../../i18n/de/SECURITY.md) · [Русский](../../i18n/ru/SECURITY.md) · **Türkçe** · [हिन्दी](../../i18n/hi/SECURITY.md) · [اردو](../../i18n/ur/SECURITY.md) · [Bahasa Indonesia](../../i18n/id/SECURITY.md) · [日本語](../../i18n/ja/SECURITY.md) · [中文](../../i18n/zh/SECURITY.md) · [한국어](../../i18n/ko/SECURITY.md)

## Bir sorunu bildirme

Lütfen güvenlik sorunlarını herkese açık bir issue yerine, bu depodaki GitHub
**Report a vulnerability** (güvenlik açığı bildir) düğmesi aracılığıyla gizli olarak bildirin. Ne
bulduğunuzu, nasıl yeniden üretileceğini ve birine neyi yapma imkânı verdiğini açıklayın.
Bildirimler en kısa sürede okunur ve yanıtlanır.

## tarjim neleri korur

- **Anahtarlar ve eşleştirme belirteci**, `keyring` aracılığıyla işletim sisteminin şifreli
  kasasında tutulur. Ayarlar dosyasında, sunucu yanıtlarında, günlüklerde ya da sohbet araçlarında
  asla görünmezler.
- **Yerel sunucu** (`tarjim-serve`) yalnızca 127.0.0.1 üzerinde dinler ve şunları reddeder:
  - belirteci (`X-Tarjim-Token`) ya da sayfanın HttpOnly, SameSite=Strict çerezi olmayan istekler;
  - `Host` değeri yerel olmayan istekler (DNS rebinding);
  - bir tarayıcı eklentisinden gelmeyen eşleştirme istekleri;
  - kendi web klasörü ve bir işin tamamlanmış çıktıları dışındaki her yol.
- **Abonelikler**, sağlayıcının kendi programı çalıştırılarak kullanılır (Claude Code, Codex,
  Copilot, Antigravity). tarjim bunların oturum açma dosyalarını veya belirteçlerini asla okumaz ya
  da saklamaz.
- **Yerel mod** medyayı cihazda tutar: modeller Hugging Face hub çevrimdışı durumdayken yüklenir ve
  ağ yalnızca kişinin istediği bir araç indirilirken kullanılır.
- **İndirmeler**: ffmpeg, sürümüyle birlikte yayımlanan SHA-256 değerine göre doğrulanır.

## Bilinen sınırlar

- Bilgisayarınızda sizin kullanıcı hesabınızla program çalıştırabilen herkes kasayı ve belirteci
  okuyabilir. tarjim, ele geçirilmiş bir hesaba karşı koruma sağlamaz.
- Seçtiğiniz bulut sağlayıcıları, işledikleri sesi veya metni kendi koşulları çerçevesinde alır.
