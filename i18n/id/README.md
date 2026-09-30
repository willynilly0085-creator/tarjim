# tarjim
<!-- languages -->
[English](../../README.md) · [العربية](../../i18n/ar/README.md) · [Español](../../i18n/es/README.md) · [Français](../../i18n/fr/README.md) · [Português](../../i18n/pt/README.md) · [Deutsch](../../i18n/de/README.md) · [Русский](../../i18n/ru/README.md) · [Türkçe](../../i18n/tr/README.md) · [हिन्दी](../../i18n/hi/README.md) · [اردو](../../i18n/ur/README.md) · **Bahasa Indonesia** · [日本語](../../i18n/ja/README.md) · [中文](../../i18n/zh/README.md) · [한국어](../../i18n/ko/README.md)

**Subtitle dan sulih suara untuk video apa pun, dalam bahasa Anda, di komputer Anda sendiri.**

Tempel tautan atau letakkan berkas. tarjim mendengarkan, menyelaraskan setiap baris dengan saat
kalimat itu diucapkan, memisahkan setiap pembicara, menerjemahkan ke dalam tuturan yang alami, lalu
menanamkan subtitle ke dalam video, menulis berkas `.srt`, atau menyulih suaranya dengan satu suara
untuk setiap pembicara.

## Apa yang dilakukannya

- **Sumber apa pun:** YouTube, X, dan tautan lain (yt-dlp), atau berkas video maupun audio apa pun di perangkat Anda.
- **34 bahasa tujuan**, baik kanan-ke-kiri maupun kiri-ke-kanan. Bahasa Arab secara bawaan memakai dialek
  Saudi; bahasa Arab Standar Modern hanya berjarak satu klik.
- **Mendengarkan dengan cermat:** audio didengarkan tiga kali dan setiap kata diputuskan lewat pemungutan
  suara, sehingga satu kali salah dengar tidak sampai ke subtitle.
- **Waktu yang tepat:** kata-kata diselaraskan dengan audio di komputer Anda (CTC forced alignment ditambah
  voice-activity detection). Subtitle tidak pernah melewati pergantian adegan hingga masuk ke adegan orang berikutnya.
- **Mengenali pembicara:** baris dialog dengan tanda pisah, satu baris per pembicara.
- **Sulih suara:** suara Gemini yang alami untuk setiap pembicara (dicocokkan menurut tinggi nada), kloning
  suara lokal tiap pembicara (VoxCPM2), suara studio, atau Fish Audio. Naskah suara terpisah menuliskan
  nama sebagaimana diucapkan dan angka sebagai kata, sehingga suara mengucapkannya dengan benar.
- **Tiga cara memakainya:** menu klik kanan di peramban ("ترجم للعربية"), halaman web lokal,
  atau obrolan: tambahkan tarjim ke aplikasi Claude, Claude Code, atau Codex lalu minta ia menerjemahkan sebuah tautan.

## Menghubungkan AI: tiga cara

| Cara | Pilihan | Catatan |
|---|---|---|
| Kunci API | Gemini, OpenAI, Anthropic, OpenRouter, DeepSeek, Qwen, Mistral, Groq, xAI, atau alamat apa pun yang kompatibel dengan OpenAI | Gemini dan OpenAI juga bisa mendengarkan (ucapan ke teks). |
| Langganan Anda | Claude (melalui Claude Code), ChatGPT (melalui Codex), GitHub Copilot, Google AI (melalui Antigravity) | tarjim menjalankan program milik vendor itu sendiri dengan akun Anda. Pemakaian dihitung dari paket Anda dan ketentuan setiap vendor berlaku. |
| Di komputer Anda | Ollama, LM Studio, Jan, llama.cpp, vLLM, KoboldCpp | Terdeteksi otomatis beserta modelnya. Tidak ada yang keluar dari perangkat Anda. |

Pilih model apa pun yang ditawarkan penyedia. Jika mesin yang dipilih gagal atau kuotanya habis, tarjim
beralih ke mesin lokal bila tersedia.

## Pasang dengan AI Anda (satu langkah)

Di Claude Code:

```bash
claude plugin marketplace add willynilly0085-creator/tarjim
claude plugin install tarjim@tarjim
```

Lalu katakan kepada AI Anda "set up tarjim". Ia memasang mesin di latar belakang (versi untuk kartu grafis
bila Anda punya kartu NVIDIA), menjalankannya tanpa jendela apa pun, dan membuka halaman penyiapan. Sejak
itu AI Anda langsung memakai alat-alat tarjim: "terjemahkan tautan ini ke bahasa Prancis dan tanamkan
subtitlenya", "pakai langganan Claude saya untuk terjemahan", "beralih ke model lokal". tarjim adalah alat
yang dioperasikan AI Anda, bukan asisten lain untuk diajak bicara. Plugin ini memerlukan
[uv](https://docs.astral.sh/uv/).

Aplikasi MCP lain (Codex, Cursor, dan lainnya): setelah mesin terpasang, tambahkan perintah `tarjim-mcp`
sebagai server MCP, misalnya `codex mcp add tarjim -- tarjim-mcp`. Codex meminta persetujuan Anda untuk
setiap panggilan alat; agar alat-alat tarjim berjalan tanpa bertanya, tambahkan
`default_tools_approval_mode = "approve"` di bawah `[mcp_servers.tarjim]` dalam `~/.codex/config.toml`.

Sudah diuji: sesi Claude Code dengan plugin ini membaca pengaturan, menetapkan glosarium, menerjemahkan
tautan YouTube ke bahasa Spanyol, dan mengembalikan subtitlenya; Codex (paket ChatGPT) membaca pengaturan
dan menetapkan glosarium. Situs web dan aplikasi desktop ChatGPT belum bisa menjangkau alat di komputer Anda
(keduanya hanya menerima server MCP jarak jauh), jadi gunakan Codex untuk ChatGPT.

## Pasang secara manual (Windows)

Memerlukan Python 3.11 dan sekitar 10 GB ruang disk untuk model lokal.

```powershell
git clone https://github.com/willynilly0085-creator/tarjim
cd tarjim
python -m venv .venv
# NVIDIA graphics card: install the CUDA build of PyTorch first (the default one is CPU only)
.venv\Scripts\python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python -m pip install -e ".[dub]"
.venv\Scripts\tarjim-serve
```

Buka <http://127.0.0.1:17653>. Halaman penyiapan memeriksa perangkat Anda, menghubungkan AI, dan mengunduh
yang Anda perlukan, termasuk ffmpeg (di Windows ffmpeg diunduh lalu dicocokkan dengan SHA-256 yang
dipublikasikan). Tanpa kartu grafis yang memadai, semuanya tetap berjalan di prosesor, hanya lebih lambat.

**macOS dan Linux** mengikuti langkah yang sama dengan `.venv/bin/...`, ditambah `brew install ffmpeg` atau
`sudo apt install ffmpeg`. Platform ini belum diuji.

### Ekstensi peramban

tarjim hadir di peramban Anda: klik kanan video atau tautan apa pun lalu pilih **ترجم للعربية** (atau bahasa
Anda), kemudian pilih subtitle, subtitle yang ditanamkan, atau sulih suara. Jendela sembulan menampilkan tahap
setiap pekerjaan dan memungkinkan Anda menjeda, membatalkan, atau membuka hasilnya.

Di Chrome buka `chrome://extensions`, aktifkan Developer mode (mode pengembang), pilih **Load unpacked**
(muat ekstensi yang belum dikemas), lalu pilih folder `~/.tarjim/extension`. Ekstensi memasangkan dirinya sendiri: tekan
**Allow** (izinkan) di halaman tarjim.

### Obrolan

Di halaman penyiapan, pada langkah "Use tarjim from a chat", tekan **Add** (tambahkan) di samping aplikasi
Claude, Claude Code, atau Codex. Setelah itu AI Anda dapat menjalankan seluruh alat untuk Anda:

- "Terjemahkan tautan ini ke bahasa Arab dan sulih suarakan", "sudah sampai tahap mana?", "jeda", "buka hasilnya";
- mengubah pengaturan: "pakai langganan Claude saya untuk terjemahan", "beralih ke model lokal",
  "tampilkan AI yang bisa saya hubungkan", "ubah antarmuka ke bahasa Inggris";
- membacakan kembali subtitle yang sudah jadi, mengulang pekerjaan yang gagal, atau mengunduh alat yang belum ada.

Kunci tidak pernah dimasukkan melalui obrolan; untuk itu AI akan membuka halaman tarjim.

### Baris perintah

```bash
tarjim video.mp4                 # Arabic (Saudi), burned into the video
tarjim video.mp4 --to fr         # any target language
tarjim video.mp4 --no-burn       # .srt and .ass only
```

## Privasi dan keamanan

- **Kunci** disimpan di brankas terenkripsi sistem operasi Anda (Windows Credential Manager,
  macOS Keychain, Secret Service). Berkas pengaturan tidak menyimpan satu pun.
- **Apa yang keluar dari perangkat Anda** bergantung pada cara Anda terhubung: audio klip dikirim ke penyedia
  pendengaran yang Anda pilih, dan teksnya ke penyedia terjemahan dan suara yang Anda pilih.
  Dalam mode lokal tidak ada yang keluar: hal ini diukur dengan mengawasi setiap koneksi selama satu pekerjaan
  lokal penuh, termasuk sulih suara (nol koneksi eksternal). Model dimuat secara luring; internet hanya dipakai
  saat Anda mengunduh sebuah alat.
- **Server lokal** hanya mendengarkan di 127.0.0.1. Setiap permintaan memerlukan token atau cookie same-site
  milik halaman, header `Host` asing ditolak (DNS rebinding), situs web tidak dapat menjangkaunya maupun
  meminta untuk dipasangkan, dan ia tidak menyajikan berkas apa pun di luar foldernya sendiri.

Lihat [SECURITY.md](SECURITY.md) untuk melaporkan masalah.

## Lisensi model

Kode tarjim tidak menyertakan bobot model; Anda mengunduhnya dari pemiliknya. Sebagian di antaranya
**tidak berlisensi untuk penggunaan komersial**:

| Alat | Lisensi | Penggunaan komersial |
|---|---|---|
| Penyelaras waktu `MahmoudAshraf/mms-300m-1130-forced-aligner` (wajib) | CC-BY-NC-4.0 | Tidak |
| Kloning suara VoxCPM2 (opsional) | Apache-2.0 | Ya |
| Terjemahan lokal `aya-expanse:8b` (opsional) | CC-BY-NC-4.0 | Tidak |
| Pendengaran lokal Qwen3-ASR-1.7B dan Qwen3-ForcedAligner | Apache-2.0 | Ya |
| ffmpeg (versi LGPL) | LGPL-2.1 | Ya |

Halaman penyiapan menampilkan setiap lisensi di samping unduhannya.

## Status

Diuji di Windows 11 dengan RTX 5080, dan dari pemasangan bersih tanpa dukungan grafis: tautan dan berkas,
subtitle yang ditanamkan dan `.srt`, bahasa Prancis dan Arab, jeda, lanjutkan, batalkan dan ulangi, ketiga
cara menghubungkan (langganan Claude dan ChatGPT, Ollama lokal), alat obrolan, dan pemeriksaan keamanan di
atas. Belum diuji: macOS, Linux, langganan GitHub Copilot dan Antigravity.

## Lisensi

tarjim gratis bagi siapa saja, termasuk perusahaan: gunakan, pelajari, ubah, dan bagikan untuk tujuan apa
pun. Satu-satunya hal yang tidak diizinkan adalah **menjualnya**: tidak seorang pun boleh menjual tarjim, atau
menjual produk atau layanan (termasuk hosting dan dukungan berbayar) yang nilainya berasal dari tarjim. Lihat
[LICENSE.md](LICENSE.md) (Apache License 2.0 dengan Commons Clause); teks lengkap yang mengikat (bahasa
Inggris) ada di [../../LICENSE](../../LICENSE).

Model yang diunduh tarjim memiliki lisensinya sendiri, dan sebagian di antaranya melarang penggunaan
komersial: periksa tabel lisensi model di atas sebelum menggunakan model tersebut untuk pekerjaan.

## Pengembangan

```bash
pip install -e ".[dub,dev]"
pytest && ruff check tarjim tests && mypy tarjim
```

Keputusan desain dan hasil pengukuran dicatat di [docs/decisions.md](../../docs/decisions.md).
Lihat [CONTRIBUTING.md](CONTRIBUTING.md).
