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

## Kitaplıklardaki bilinen sorunlar

tarjim'in kurduğu kitaplıklarda yayımlanmış ve hiçbir test edilmiş sürümün henüz önleyemediği açıklar: şu an yok. Biri çıkarsa bilgileri tarjim ile birlikte `tarjim/known_issues.json` içinde gelir: **Ayarlar**, motorun `/update` yanıtı ve sohbet araçlarının `setup_status` çıktısı onu kurulu sürümü etkilenen bilgisayarlarda gösterir; bir güncelleme düzeltilmiş sürümü kurduğunda kendiliğinden kaybolur. CI burada listelenmeyen her açıkta başarısız olur ve haftalık bir kontrol listedeki biri düzeltilebildiğinde haber verir.

**2026-10-23'te kapandı.** O zamanki yerel dinleme motoru qwen-asr, transformers'ı 4.57.6'da tuttuğu sürece altı transformers uyarısı (PYSEC-2025-217, PYSEC-2026-2288, PYSEC-2026-2289, PYSEC-2026-2290, PYSEC-2026-3929, PYSEC-2026-4174) açık kaldı. Yerel dinleme artık Transformers'ın kendi Qwen3-ASR modelleriyle çalışıyor; bu yüzden tarjim transformers 5.20.2'yi kuruyor ve qwen-asr'ı artık kurmuyor. accelerate hiçbir istisna olmadan 1.15.0'da kalıyor (PYSEC-2026-3804 kapandı).

**tarjim'in her durumda yaptığı.** Her Hugging Face modeli sabit bir commit'ten (`tarjim/model_pins.py`) indirilir; yalnızca ayarları, tokenizer'ı, sohbet şablonu ve safetensors dosyaları, asla kod değil. Büyük dosyaları yayımlanan SHA-256 ile eşleşmek zorundadır ve model, hub çevrimdışıyken bilgisayardaki o klasörden yüklenir. `trust_remote_code` hiç açılmaz ve `kernels` paketi kurulu değildir. Ses ayırma ağırlıkları yalnızca demucs'un kendi model sınıfını adlandırırsa, hareke modeli de yalnızca iki dosyası sürümünün SHA-256'sı ile eşleşirse yüklenir.
