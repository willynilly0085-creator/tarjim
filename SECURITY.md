# Security
<!-- languages -->
**English** · [العربية](i18n/ar/SECURITY.md) · [Español](i18n/es/SECURITY.md) · [Français](i18n/fr/SECURITY.md) · [Português](i18n/pt/SECURITY.md) · [Deutsch](i18n/de/SECURITY.md) · [Русский](i18n/ru/SECURITY.md) · [Türkçe](i18n/tr/SECURITY.md) · [हिन्दी](i18n/hi/SECURITY.md) · [اردو](i18n/ur/SECURITY.md) · [Bahasa Indonesia](i18n/id/SECURITY.md) · [日本語](i18n/ja/SECURITY.md) · [中文](i18n/zh/SECURITY.md) · [한국어](i18n/ko/SECURITY.md)

## Reporting a problem

Please report security problems privately through GitHub's "Report a vulnerability" button on this
repository, not in a public issue. Describe what you found, how to reproduce it, and what it lets
someone do. Reports are read and answered as soon as possible.

## What tarjim protects

- **Keys and the pairing token** live in the operating system's encrypted vault through `keyring`.
  They never appear in server responses, in logs or in chat tools, and not in the settings file
  either, except on a computer with no vault backend (some Linux servers), where they are kept
  in the settings file with owner-only permissions.
- **The local server** (`tarjim-serve`) listens on 127.0.0.1 only and refuses:
  - requests without the token (`X-Tarjim-Token`) or the page's HttpOnly, SameSite=Strict cookie
    (the cookie is derived from the token, is not the token, and counts only on requests the
    browser marks `Sec-Fetch-Site: same-origin` or `none`);
  - requests whose `Host` is not local (DNS rebinding);
  - pairing requests that do not come from a browser extension;
  - any path outside its own web folder and the finished outputs of a job.
- **Subscriptions** are used by running the vendor's own program (Claude Code, Codex, Copilot,
  Antigravity). tarjim never reads or stores their sign-in files or tokens.
- **Local mode** keeps media on the device: models load with the Hugging Face hub offline, and the
  network is used only while downloading a tool the person asked for.
- **Downloads**: ffmpeg is checked against the SHA-256 published with its release.

## Known limits

- Anyone who can run programs as your user on your computer can read the vault and the token.
  tarjim does not defend against a compromised account.
- Cloud providers you choose receive the audio or text they process, under their own terms.

## Known library issues

Published vulnerabilities in libraries tarjim installs that no tested version can avoid yet: none at the moment. If one appears, its facts ship with tarjim in `tarjim/known_issues.json`: **Settings**, the engine's `/update` answer and the chat tools' `setup_status` show it on the computers whose installed version it applies to, and it disappears by itself once an update installs a fixed version. CI fails on any vulnerability not listed here, and a weekly check reports when a listed one can be fixed.

**Closed on 2026-10-23.** Six transformers advisories (PYSEC-2025-217, PYSEC-2026-2288, PYSEC-2026-2289, PYSEC-2026-2290, PYSEC-2026-3929, PYSEC-2026-4174) stayed open while qwen-asr, the local listening engine of that time, held transformers at 4.57.6. Local listening now runs Transformers' own Qwen3-ASR models, so tarjim installs transformers 5.20.2 and no longer installs qwen-asr; accelerate stays at 1.15.0 (PYSEC-2026-3804 closed) without any override.

**What tarjim does in any case.** Every Hugging Face model is downloaded at one fixed commit (`tarjim/model_pins.py`), only its settings, tokenizer, chat template and safetensors files, never code; its large files must match their published SHA-256, and it is loaded from that folder on the computer with the hub offline. `trust_remote_code` is never set, and the `kernels` package is not installed. The voice separation weights load only if they name demucs' own model class, and the diacritics model only if both files match the SHA-256 of their release.
