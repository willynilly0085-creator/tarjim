# tarjim
<!-- languages -->
[English](../../README.md) · [العربية](../../i18n/ar/README.md) · [Español](../../i18n/es/README.md) · [Français](../../i18n/fr/README.md) · [Português](../../i18n/pt/README.md) · [Deutsch](../../i18n/de/README.md) · [Русский](../../i18n/ru/README.md) · **Türkçe** · [हिन्दी](../../i18n/hi/README.md) · [اردو](../../i18n/ur/README.md) · [Bahasa Indonesia](../../i18n/id/README.md) · [日本語](../../i18n/ja/README.md) · [中文](../../i18n/zh/README.md) · [한국어](../../i18n/ko/README.md)

[Indicators](https://indicators.sa/) tarafından geliştirildi · [indicators.sa](https://indicators.sa/)

**Her video için altyazı ve seslendirme; sizin dilinizde, kendi bilgisayarınızda.**

Bir bağlantı yapıştırın ya da bir dosya bırakın. tarjim dinler, her satırı söylendiği ana göre
zamanlar, konuşmacıları birbirinden ayırır, doğal bir konuşma diline çevirir ve altyazıları videoya
gömer, bir `.srt` dosyası yazar ya da videoyu her konuşmacı için ayrı bir sesle seslendirir.

## Neler yapar

- **Her kaynak:** YouTube, X ve diğer bağlantılar (yt-dlp) ya da cihazınızdaki herhangi bir video
  veya ses dosyası.
- **34 hedef dil**, sağdan sola ve soldan sağa yazılanlar dahil. Arapça için varsayılan Suudi
  lehçesidir; Modern Standart Arapça bir tık uzağınızda.
- **Dikkatli dinleme:** ses üç kez dinlenir ve her kelime oylanır; böylece tek bir yanlış duyma
  altyazıya yansımaz.
- **Kesin zamanlama:** kelimeler bilgisayarınızda sese hizalanır (CTC zorunlu hizalama ve ses
  etkinliği algılama). Altyazılar hiçbir zaman bir sahne kesmesini aşıp sonraki kişinin çekimine
  taşmaz.
- **Konuşmacıyı tanır:** tireli diyalog satırları, her konuşmacı için bir satır.
- **Seslendirme:** her konuşmacı için doğal bir Gemini sesi (ses perdesine göre eşleştirilir), her
  konuşmacının yerel bir ses klonu (VoxCPM2), stüdyo sesleri ya da Fish Audio. Ayrı bir seslendirme
  metni adları okunduğu gibi, sayıları da yazıyla yazar; böylece ses bunları doğru söyler.
- **Üç kullanım yolu:** tarayıcıda sağ tık menüsü ("ترجم للعربية"), yerel bir web sayfası ya da bir
  sohbet: tarjim'i Claude uygulamasına, Claude Code'a veya Codex'e ekleyin ve bir bağlantıyı
  çevirmesini isteyin.

## Bir yapay zekâ bağlayın: üç yol

| Yol | Seçenekler | Notlar |
|---|---|---|
| API anahtarı | Gemini, OpenAI, Anthropic, OpenRouter, DeepSeek, Qwen, Mistral, Groq, xAI ya da OpenAI uyumlu herhangi bir adres | Gemini ve OpenAI dinleyebilir de (konuşmadan metne). |
| Aboneliğiniz | Claude (Claude Code üzerinden), ChatGPT (Codex üzerinden), Grok (Grok Build üzerinden), GitHub Copilot, Google AI (Antigravity üzerinden) | tarjim, sağlayıcının kendi programını sizin oturumunuzla çalıştırır. Kullanım planınızdan düşülür ve her sağlayıcının kendi koşulları geçerlidir. |
| Bilgisayarınızda | Ollama, LM Studio, Jan, llama.cpp, vLLM, KoboldCpp | Modelleriyle birlikte otomatik olarak bulunur. Hiçbir şey cihazınızdan çıkmaz. |

Bir sağlayıcının sunduğu herhangi bir modeli seçin. Seçilen motor başarısız olursa ya da kotası
biterse, tarjim varsa yerel motora geçer.

## Bilgisayarınızın neye ihtiyacı var

Ağır işler isteğe bağlıdır. Neye ihtiyacınız olduğu, hangi parçaların kendi bilgisayarınızda
çalıştığına bağlıdır:

| Ne kullandığınız | Ekran kartı | Bellek (RAM) | Boş disk alanı |
|---|---|---|---|
| Bağladığınız bir yapay zekâyla altyazı (bir Gemini anahtarı, bir Claude veya ChatGPT aboneliği, herhangi bir API anahtarı) | Gerekmez | 8 GB | yaklaşık 6 GB |
| Doğal veya stüdyo seslerle seslendirme | Gerekmez | 8 GB | ek alan gerekmez |
| Bu bilgisayarda dinleme (ses bilgisayardan asla çıkmaz) | NVIDIA, 8 GB | 16 GB | 6.3 GB daha |
| Bu bilgisayarda çeviri (Ollama ile aya-expanse 8B) | 8 GB | 16 GB | 5.1 GB daha |
| Her konuşmacının kendi sesiyle seslendirme | NVIDIA, 8 GB | 16 GB | 4.7 GB daha |

- **Sistem:** Windows 10 veya 11, 64 bit. macOS ve Linux aynı kodu çalıştırır ama henüz test
  edilmedi.
- **İnternet:** indirmeler ve bağladığınız yapay zekâ için. Dinleme ve çeviri bu bilgisayarda
  yapılıyorsa, her şey indirildikten sonra işler çevrimdışı çalışır.
- **NVIDIA kartı yoksa** her şey yine de işlemci üzerinde çalışır, yalnızca çok daha yavaş;
  konuşmacının kendi sesiyle seslendirme orada pratik değildir.
- **Aynı anda tek model:** tarjim, bir sonraki model yüklenmeden önce her modeli boşaltır; bu yüzden
  ekran kartında tüm modellere birlikte değil, yalnızca en büyüğüne (yaklaşık 6 GB) yetecek yer
  olması gerekir.
- **Her şey bu bilgisayarda:** yaklaşık 22 GB disk.

Windows 11 üzerinde, RTX 5080 (16 GB) ve 32 GB RAM ile ölçüldü: kartta dinleme en fazla 5.9 GB ekran
belleği kullandı, aya-expanse 8B ile çeviri 5.7 GB, konuşmacının kendi sesi ise 6.1 GB; cümle başına
yaklaşık 3 saniye sürdü. Konuşmacı sesi modelini yüklemek, 2.5 GB düzeyine inmeden önce kısa
süreliğine yaklaşık 11 GB RAM kullanır; 16 GB istenmesinin nedeni budur. Motorun kendisi (Python ile
PyTorch'un ekran kartı sürümü) yukarıdaki disk rakamlarının içinde yaklaşık 4 GB yer tutar.

## Yapay zekânızla kurun (tek adım)

Claude Code'da:

```bash
claude plugin marketplace add willynilly0085-creator/tarjim
claude plugin install tarjim@tarjim
```

Ardından yapay zekânıza "tarjim'i kur" deyin. Motoru arka planda kurar (NVIDIA kartınız varsa ekran
kartı sürümünü), hiçbir pencere açmadan başlatır ve kurulum sayfasını açar. Bundan sonra yapay
zekânız tarjim'in araçlarını doğrudan kullanır: "bu bağlantıyı Fransızcaya çevir ve altyazıları
göm", "çeviri için Claude aboneliğimi kullan", "yerel modele geç". tarjim, yapay zekânızın
kullandığı bir araçtır; sohbet edeceğiniz bir asistan daha değildir. Eklenti için
[uv](https://docs.astral.sh/uv/) gerekir.

Diğer MCP uygulamaları (Codex, Cursor ve daha fazlası): motor kurulduktan sonra `tarjim-mcp`
komutunu bir MCP sunucusu olarak ekleyin; örneğin `codex mcp add tarjim -- tarjim-mcp`. Codex her
araç çağrısı için onay ister; tarjim'in araçlarının sormadan çalışması için `~/.codex/config.toml`
dosyasında `[mcp_servers.tarjim]` altına `default_tools_approval_mode = "approve"` ekleyin.

Test edildi: eklentili bir Claude Code oturumu ayarları okudu, sözlüğü ayarladı, bir YouTube
bağlantısını İspanyolcaya çevirdi ve altyazıları döndürdü; Codex (ChatGPT planı) ayarları okudu ve
sözlüğü ayarladı. ChatGPT web sitesi ve masaüstü uygulaması henüz bilgisayarınızdaki araçlara
erişemiyor (yalnızca uzak MCP sunucularını kabul ediyorlar); bu yüzden ChatGPT için Codex'i
kullanın.

## Elle kurulum (Windows)

Python 3.11 gerekir. Disk, bellek ve ekran kartı için bkz. [Bilgisayarınızın neye ihtiyacı var](#bilgisayarınızın-neye-ihtiyacı-var).

```powershell
git clone https://github.com/willynilly0085-creator/tarjim
cd tarjim
python -m venv .venv
# NVIDIA graphics card: install the CUDA build of PyTorch first (the default one is CPU only)
.venv\Scripts\python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python -m pip install -e ".[dub]"
.venv\Scripts\tarjim-serve
```

<http://127.0.0.1:17653> adresini açın. Kurulum sayfası cihazınızı denetler, bir yapay zekâ bağlar
ve ffmpeg dahil ihtiyacınız olanları indirir (Windows'ta ffmpeg indirilir ve yayımlanmış SHA-256
değerine göre doğrulanır). Kullanılabilir bir ekran kartı olmasa da her şey işlemci üzerinde
çalışmaya devam eder, yalnızca daha yavaş.

**macOS ve Linux** aynı adımları `.venv/bin/...` ile izler; ek olarak `brew install ffmpeg` ya da
`sudo apt install ffmpeg` gerekir. Bu platformlar henüz test edilmedi.

### Tarayıcı eklentisi

tarjim tarayıcınızda yaşar: herhangi bir videoya veya bağlantıya sağ tıklayıp **ترجم للعربية** (ya da
kendi dilinizi) seçin, ardından altyazı, gömülü altyazı veya seslendirmeyi seçin. Açılır pencere her
işin aşamasını gösterir ve işi duraklatmanıza, iptal etmenize ya da sonucu açmanıza olanak tanır.

Chrome'da `chrome://extensions` sayfasını açın, Developer mode (geliştirici modu) seçeneğini açın,
**Load unpacked** (paketlenmemiş öğe yükle) seçeneğini seçin ve `~/.tarjim/extension` klasörünü gösterin.
Eklenti kendiliğinden eşleşir: tarjim sayfasında **Allow** (izin ver) düğmesine basın.

### Sohbet

Kurulum sayfasındaki "Use tarjim from a chat" (tarjim'i bir sohbetten kullan) adımında, Claude
uygulaması, Claude Code veya Codex'in yanındaki **Add** (ekle) düğmesine basın. Ardından yapay
zekânız tüm aracı sizin için çalıştırabilir:

- "Bu bağlantıyı Arapçaya çevir ve seslendir", "hangi aşamada?", "duraklat", "sonucu aç";
- ayarları değiştirmek: "çeviri için Claude aboneliğimi kullan", "yerel modele geç", "bağlayabileceğim
  yapay zekâları listele", "arayüzü İngilizce yap";
- bitmiş altyazıları size okumak, başarısız bir işi yeniden denemek ya da eksik bir aracı indirmek.

Anahtarlar hiçbir zaman sohbet üzerinden girilmez; bunun için yapay zekâ tarjim sayfasını açar.

### Telefon

Kendi Telegram botunuza herhangi bir telefondan, iPhone ya da Android, evde veya dışarıda bir
video bağlantısı gönderin; çevrilmiş video aynı sohbette size geri gelir. Ayarlar'da **Telefon**
bölümünü açın: BotFather'da bir bot oluşturun (`/newbot`), belirtecini (token) yapıştırın
(bilgisayarınızın kasasında kalır), ardından QR kodunu telefonunuzla tarayın ve **Başlat**
düğmesine basın. Bot yalnızca sizin hesabınıza yanıt verir ve yeni mesajları Telegram'dan
bilgisayarınız kendisi sorar; bu yüzden internete hiçbir port açılmaz. Dil, sonuç ve stil
Ayarlar'dan gelir; bottaki `/mode` sonucu değiştirir. Telegram, botların 20 MB'a kadar video
indirmesine ve 50 MB'a kadar dosya göndermesine izin verir: daha büyük bir sonuç sığması için
yeniden kodlanır ya da altyazı dosyasını alırsınız ve videonun tamamı bilgisayarınızda kalır.
Bot, bilgisayarınız ve tarjim çalıştığı sürece yanıt verir.

### Komut satırı

```bash
tarjim video.mp4                 # Arabic (Saudi), burned into the video
tarjim video.mp4 --to fr         # any target language
tarjim video.mp4 --no-burn       # .srt and .ass only
```

## Güncellemeler

tarjim kendini güncel tutar. Motor günde bir kez GitHub'a en son sürümün numarasını sorar: sizinle
ya da videolarınızla ilgili hiçbir şey taşımayan tek bir istek. **Yeni sürüm çıkınca tarjim'i
otomatik güncelle** açıkken (kurulum sırasında sunulur ve Ayarlar'dan değiştirilebilir), daha yeni
bir sürüm, çalışan bir iş olmadığı sürece arka planda kurulur ve tarjim birkaç dakika içinde
kendiliğinden geri gelir; tarayıcı eklentisi de buna uymak için kendini yeniler. Kapalıyken sayfa
bir uyarı ve bir **Şimdi güncelle** düğmesi gösterir. Kaynaktan çalıştırdığınız kopya `git pull` ile
güncellenir.

## Gizlilik ve güvenlik

- **Anahtarlar** işletim sisteminizin şifreli kasasında saklanır (Windows Credential Manager, macOS
  Keychain, Secret Service). Ayarlar dosyasında hiçbiri yer almaz.
- **Cihazınızdan neyin çıktığı** bağlanma yolunuza bağlıdır: klibin sesi seçtiğiniz dinleme
  sağlayıcısına, metin ise seçtiğiniz çeviri ve ses sağlayıcılarına gider. Yerel modda hiçbir şey
  dışarı çıkmaz: bu, seslendirme dahil tam bir yerel iş boyunca her bağlantı izlenerek ölçüldü
  (sıfır dış bağlantı). Modeller çevrimdışı yüklenir; internet yalnızca bir araç indirdiğinizde
  kullanılır.
- **Yerel sunucu** yalnızca 127.0.0.1 üzerinde dinler. Her istek bir belirteç ya da sayfanın
  same-site çerezini gerektirir, yabancı `Host` başlıkları reddedilir (DNS rebinding), web siteleri
  ona erişemez veya eşleştirme isteyemez ve sunucu kendi klasörleri dışında hiçbir dosya sunmaz.

Bir sorunu bildirmek için [SECURITY.md](SECURITY.md) dosyasına bakın.

## Model lisansları

tarjim'in kodu model ağırlıklarını içermez; bunları sahiplerinden indirirsiniz. Bazıları **ticari
kullanım için lisanslı değildir**:

| Araç | Lisans | Ticari kullanım |
|---|---|---|
| Zamanlama hizalayıcı `MahmoudAshraf/mms-300m-1130-forced-aligner` (zorunlu) | CC-BY-NC-4.0 | Hayır |
| Ses klonu VoxCPM2 (isteğe bağlı) | Apache-2.0 | Evet |
| Yerel çeviri `aya-expanse:8b` (isteğe bağlı) | CC-BY-NC-4.0 | Hayır |
| Yerel dinleme Qwen3-ASR-1.7B ve Qwen3-ForcedAligner | Apache-2.0 | Evet |
| ffmpeg (LGPL derlemesi) | LGPL-2.1 | Evet |

Kurulum sayfası her lisansı ilgili indirmenin yanında gösterir.

## Durum

Windows 11'de bir RTX 5080 ile ve ekran kartı desteği olmayan temiz bir kurulumda test edildi:
bağlantılar ve dosyalar, gömülü altyazılar ve `.srt`, Fransızca ve Arapça, duraklatma, sürdürme,
iptal ve yeniden deneme, üç bağlanma yolu (Claude ve ChatGPT abonelikleri, yerel Ollama), sohbet
araçları, konuşmacının kendi sesiyle seslendirme (İngilizceden Suudi Arapçasına) ve yukarıdaki
güvenlik denetimleri. Henüz test edilmedi: macOS, Linux, GitHub Copilot ve Antigravity
abonelikleri ile telefon botunun gerçek Telegram hizmetiyle çalışması (kodu, simüle edilmiş bir
Telegram ile yapılan testlerle kapsanıyor).

## Lisans

tarjim, şirketler dahil herkes için ücretsizdir: onu her amaçla kullanabilir, inceleyebilir,
değiştirebilir ve paylaşabilirsiniz. İzin verilmeyen tek şey **onu satmaktır**: kimse tarjim'i ya
da değerini tarjim'den alan bir ürünü veya hizmeti (barındırma ve ücretli destek dahil) satamaz.
Bkz. [LICENSE.md](LICENSE.md) (Apache License 2.0, Commons Clause ile); bağlayıcı tam metin
[LICENSE](../../LICENSE) dosyasındadır.

tarjim'in indirdiği modellerin kendi lisansları vardır ve bazıları ticari kullanımı yasaklar: bu
modelleri iş için kullanmadan önce yukarıdaki model lisansları tablosuna bakın.

## Geliştirme

```bash
pip install -e ".[dub,dev]"
pytest && ruff check tarjim tests && mypy tarjim
```

Tasarım kararları ve ölçümler [docs/decisions.md](../../docs/decisions.md) dosyasına kaydedilir.
Bkz. [CONTRIBUTING.md](CONTRIBUTING.md).
