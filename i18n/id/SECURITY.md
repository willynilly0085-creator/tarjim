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
