# Berkontribusi
<!-- languages -->
[English](../../CONTRIBUTING.md) · [العربية](../../i18n/ar/CONTRIBUTING.md) · [Español](../../i18n/es/CONTRIBUTING.md) · [Français](../../i18n/fr/CONTRIBUTING.md) · [Português](../../i18n/pt/CONTRIBUTING.md) · [Deutsch](../../i18n/de/CONTRIBUTING.md) · [Русский](../../i18n/ru/CONTRIBUTING.md) · [Türkçe](../../i18n/tr/CONTRIBUTING.md) · [हिन्दी](../../i18n/hi/CONTRIBUTING.md) · [اردو](../../i18n/ur/CONTRIBUTING.md) · **Bahasa Indonesia** · [日本語](../../i18n/ja/CONTRIBUTING.md) · [中文](../../i18n/zh/CONTRIBUTING.md) · [한국어](../../i18n/ko/CONTRIBUTING.md)

Terima kasih telah membantu. Beberapa aturan menjaga tarjim tetap mudah dibaca dan aman diubah.

## Sebelum Anda membuka pull request

```bash
pip install -e ".[dub,dev]"
pytest
ruff check tarjim tests
mypy tarjim
```

Keempatnya harus lolos. Batasannya ditegakkan oleh konfigurasi di `pyproject.toml`: berkas di bawah 200 baris,
fungsi di bawah 20 pernyataan dengan kompleksitas 6 atau kurang, paling banyak 4 argumen, baris di bawah
100 karakter, `mypy --strict`.

## Cara perubahan dibuat di sini

- Tulis dulu tes yang gagal, lalu kode yang membuatnya lolos.
- Ukur sebelum mengklaim: perubahan waktu, kualitas, dan kecepatan disertai angka yang membuktikannya,
  dicatat sebagai satu baris bertanggal di `docs/decisions.md` (hanya ditambahkan, tidak diubah).
- Nama membawa makna; komentar hanya menjelaskan apa yang tidak bisa disampaikan kode.
- Teks antarmuka berada di berkas bahasa (`tarjim/web/i18n`, `extension/_locales`), dalam bahasa Arab Saudi
  yang sederhana dan bahasa Inggris. Tidak ada emoji di antarmuka.
- Tidak ada yang boleh mengirim media atau kunci seseorang ke tempat yang tidak ia pilih. Mode lokal harus
  tetap pada nol koneksi eksternal.
