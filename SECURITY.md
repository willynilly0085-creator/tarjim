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

Published vulnerabilities in libraries tarjim installs that no tested version can avoid yet. The
same facts ship with tarjim in `tarjim/known_issues.json`: **Settings**, the engine's `/update`
answer and the chat tools' `setup_status` show the ones that apply to the versions installed on
that computer, and each one disappears by itself once an update installs a fixed version. CI fails
on any vulnerability not listed here, and a weekly check reports when one of these can be fixed.

**Why they remain.** qwen-asr 0.0.6, the local listening engine, requires transformers 4.57.6
exactly, and every transformers 5 release stops it from loading (checked on 2026-10-15: with 5.0
and 5.1 the model cannot be built, `KeyError: 'default'` in its rotary embedding; 5.2 and 5.3 no
longer have `check_model_inputs`; from 5.5 on that decorator takes different arguments). The fix
arrives when qwen-asr allows transformers 5, or when tarjim moves to the Transformers-native
Qwen3-ASR models published in June 2026. accelerate, which qwen-asr also pins exactly, is
installed at 1.15.0 (`tarjim/overrides.txt`), which closes PYSEC-2026-3804; the words heard and
their timings were the same with it.

**What tarjim does against all of them.** Every Hugging Face model is downloaded at one fixed
commit (`tarjim/model_pins.py`), only its settings, tokenizer and safetensors files, never code,
and is loaded from that folder on the computer with the hub offline; `trust_remote_code` is never
set, and the `kernels` package is not installed. The voice separation weights load only if they
name demucs' own model class, and the diacritics model only if both files match the SHA-256 of
their release.

- **PYSEC-2025-217** (CVE-2025-14929): transformers `<=5.0.0rc0`, fixed in 5.0.0.
  What it is: A tool that converts X-CLIP model checkpoints could run code hidden in a checkpoint file.
  Reached by tarjim: no. tarjim never converts checkpoints and never loads X-CLIP models.
  Where the fix comes from: transformers 5.0.0. tarjim installs it once qwen-asr, its listening engine, allows transformers 5 (qwen-asr 0.0.6 requires 4.57.6 exactly, and stops loading with any 5.x release).
- **PYSEC-2026-2288** (CVE-2026-1839, GHSA-69w3-r845-3855): transformers `<5.0.0`, fixed in 5.0.0.
  What it is: Resuming a training run from a crafted checkpoint could run code, when PyTorch is older than 2.6.
  Reached by tarjim: no. tarjim never trains models, so it never resumes from a checkpoint.
  Where the fix comes from: transformers 5.0.0. tarjim installs it once qwen-asr, its listening engine, allows transformers 5 (qwen-asr 0.0.6 requires 4.57.6 exactly, and stops loading with any 5.x release).
- **PYSEC-2026-2289** (CVE-2026-4372, GHSA-29pf-2h5f-8g72): transformers `<5.3.0`, fixed in 5.3.0.
  What it is: A model whose config.json was written by an attacker could make transformers fetch and run code from another repository.
  Reached by tarjim: no. tarjim loads only its own models, each from one fixed commit it checked, from a folder on this computer and offline, so a changed config.json never reaches it; the kernels package this needs is not installed either.
  Where the fix comes from: transformers 5.3.0. tarjim installs it once qwen-asr, its listening engine, allows transformers 5 (qwen-asr 0.0.6 requires 4.57.6 exactly, and stops loading with any 5.x release).
- **PYSEC-2026-2290** (CVE-2026-5241, GHSA-fgcw-684q-jj6r): transformers `<5.5.0`, fixed in 5.5.0.
  What it is: Loading a LightGlue model from an attacker's repository could run its code even with remote code switched off.
  Reached by tarjim: no. tarjim never loads LightGlue models; its own models come from fixed commits it checked.
  Where the fix comes from: transformers 5.5.0. tarjim installs it once qwen-asr, its listening engine, allows transformers 5 (qwen-asr 0.0.6 requires 4.57.6 exactly, and stops loading with any 5.x release).
- **PYSEC-2026-3929** (CVE-2026-9856, GHSA-xrqw-3rrv-vx5w): transformers `<5.10.0`, fixed in 5.10.0.
  What it is: Saving a tokenizer that came from a crafted repository could write files outside the chosen folder.
  Reached by tarjim: no. tarjim never saves a tokenizer or processor that way (save_pretrained), and its models come from fixed commits it checked.
  Where the fix comes from: transformers 5.10.0. tarjim installs it once qwen-asr, its listening engine, allows transformers 5 (qwen-asr 0.0.6 requires 4.57.6 exactly, and stops loading with any 5.x release).
- **PYSEC-2026-4174** (CVE-2026-80047, GHSA-x9r9-c232-4q39): transformers `>=4.49.0,<=5.8.1`, fixed in 5.9.0.
  What it is: Loading a model from a repository that carries custom generation code saves that code to disk before asking for permission; it is not run.
  Reached by tarjim: no. tarjim downloads only the model files it needs, never code, from fixed commits it checked, and loads them from a folder on this computer, so no such code is fetched.
  Where the fix comes from: transformers 5.9.0. tarjim installs it once qwen-asr, its listening engine, allows transformers 5 (qwen-asr 0.0.6 requires 4.57.6 exactly, and stops loading with any 5.x release).
