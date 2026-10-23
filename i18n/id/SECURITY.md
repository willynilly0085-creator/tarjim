# Keamanan
<!-- languages -->
[English](../../SECURITY.md) · [العربية](../../i18n/ar/SECURITY.md) · [Español](../../i18n/es/SECURITY.md) · [Français](../../i18n/fr/SECURITY.md) · [Português](../../i18n/pt/SECURITY.md) · [Deutsch](../../i18n/de/SECURITY.md) · [Русский](../../i18n/ru/SECURITY.md) · [Türkçe](../../i18n/tr/SECURITY.md) · [हिन्दी](../../i18n/hi/SECURITY.md) · [اردو](../../i18n/ur/SECURITY.md) · **Bahasa Indonesia** · [日本語](../../i18n/ja/SECURITY.md) · [中文](../../i18n/zh/SECURITY.md) · [한국어](../../i18n/ko/SECURITY.md)

## Melaporkan masalah

Laporkan masalah keamanan secara pribadi melalui tombol "Report a vulnerability" (laporkan kerentanan) milik
GitHub di repositori ini, bukan di issue publik. Jelaskan apa yang Anda temukan, cara mereproduksinya, dan apa
yang dapat dilakukan seseorang dengannya. Laporan dibaca dan ditanggapi secepat mungkin.

## Apa yang dilindungi tarjim

- **Kunci dan token pemasangan** disimpan di brankas terenkripsi sistem operasi melalui `keyring`.
  Keduanya tidak pernah muncul di berkas pengaturan, respons server, log, atau alat obrolan.
- **Server lokal** (`tarjim-serve`) hanya mendengarkan di 127.0.0.1 dan menolak:
  - permintaan tanpa token (`X-Tarjim-Token`) atau cookie HttpOnly, SameSite=Strict milik halaman;
  - permintaan yang `Host`-nya bukan lokal (DNS rebinding);
  - permintaan pemasangan yang tidak berasal dari ekstensi peramban;
  - jalur apa pun di luar folder web miliknya sendiri dan hasil akhir sebuah pekerjaan.
- **Langganan** digunakan dengan menjalankan program milik vendor itu sendiri (Claude Code, Codex, Copilot,
  Antigravity). tarjim tidak pernah membaca atau menyimpan berkas masuk maupun token mereka.
- **Mode lokal** menjaga media tetap di perangkat: model dimuat dengan Hugging Face hub dalam keadaan luring,
  dan jaringan hanya dipakai saat mengunduh alat yang diminta pengguna.
- **Unduhan**: ffmpeg dicocokkan dengan SHA-256 yang dipublikasikan bersama rilisnya.

## Batasan yang diketahui

- Siapa pun yang dapat menjalankan program sebagai pengguna Anda di komputer Anda dapat membaca brankas dan token.
  tarjim tidak melindungi dari akun yang telah disusupi.
- Penyedia cloud yang Anda pilih menerima audio atau teks yang mereka proses, di bawah ketentuan mereka sendiri.

## Masalah yang diketahui di pustaka

Kerentanan yang dipublikasikan di pustaka yang dipasang tarjim dan belum bisa dihindari versi teruji mana pun: saat ini tidak ada. Jika muncul, datanya ikut bersama tarjim di `tarjim/known_issues.json`: **Pengaturan**, jawaban `/update` dari mesin, dan `setup_status` di alat chat menampilkannya di komputer yang versi terpasangnya terdampak, dan ia hilang sendiri begitu pembaruan memasang versi yang sudah diperbaiki. CI gagal untuk kerentanan apa pun yang tidak tercantum di sini, dan pemeriksaan mingguan memberi tahu saat yang tercantum bisa diperbaiki.

**Ditutup pada 2026-10-23.** Enam peringatan transformers (PYSEC-2025-217, PYSEC-2026-2288, PYSEC-2026-2289, PYSEC-2026-2290, PYSEC-2026-3929, PYSEC-2026-4174) tetap terbuka selama qwen-asr, mesin pendengar lokal waktu itu, menahan transformers di 4.57.6. Pendengaran lokal kini memakai model Qwen3-ASR milik Transformers sendiri, jadi tarjim memasang transformers 5.20.2 dan tidak lagi memasang qwen-asr; accelerate tetap di 1.15.0 (PYSEC-2026-3804 ditutup) tanpa pengecualian apa pun.

**Yang selalu dilakukan tarjim.** Setiap model Hugging Face diunduh dari satu commit tetap (`tarjim/model_pins.py`), hanya pengaturan, tokenizer, templat chat, dan berkas safetensors-nya, tidak pernah kode; berkas besarnya harus cocok dengan SHA-256 yang dipublikasikan, dan dimuat dari folder itu di komputer dengan hub luring. `trust_remote_code` tidak pernah diaktifkan, dan paket `kernels` tidak terpasang. Bobot pemisah suara hanya dimuat jika menyebut kelas model milik demucs, dan model harakat hanya jika kedua berkasnya cocok dengan SHA-256 rilisnya.
