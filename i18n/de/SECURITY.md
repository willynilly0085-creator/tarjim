# Sicherheit
<!-- languages -->
[English](../../SECURITY.md) · [العربية](../../i18n/ar/SECURITY.md) · [Español](../../i18n/es/SECURITY.md) · [Français](../../i18n/fr/SECURITY.md) · [Português](../../i18n/pt/SECURITY.md) · **Deutsch** · [Русский](../../i18n/ru/SECURITY.md) · [Türkçe](../../i18n/tr/SECURITY.md) · [हिन्दी](../../i18n/hi/SECURITY.md) · [اردو](../../i18n/ur/SECURITY.md) · [Bahasa Indonesia](../../i18n/id/SECURITY.md) · [日本語](../../i18n/ja/SECURITY.md) · [中文](../../i18n/zh/SECURITY.md) · [한국어](../../i18n/ko/SECURITY.md)

## Ein Problem melden

Bitte melden Sie Sicherheitsprobleme vertraulich über die GitHub-Schaltfläche
**Report a vulnerability** (Sicherheitslücke melden) in diesem Repository, nicht in einem
öffentlichen Issue. Beschreiben Sie, was Sie gefunden haben, wie es sich reproduzieren lässt und was
es jemandem ermöglicht. Meldungen werden so schnell wie möglich gelesen und beantwortet.

## Was tarjim schützt

- **Schlüssel und das Kopplungstoken** liegen über `keyring` im verschlüsselten Tresor des
  Betriebssystems. Sie erscheinen nie in der Einstellungsdatei, in Serverantworten, in Protokollen
  oder in Chat-Werkzeugen.
- **Der lokale Server** (`tarjim-serve`) lauscht nur auf 127.0.0.1 und weist Folgendes ab:
  - Anfragen ohne das Token (`X-Tarjim-Token`) oder das HttpOnly-, SameSite=Strict-Cookie der Seite;
  - Anfragen, deren `Host` nicht lokal ist (DNS-Rebinding);
  - Kopplungsanfragen, die nicht von einer Browser-Erweiterung stammen;
  - jeden Pfad außerhalb seines eigenen Web-Ordners und der fertigen Ausgaben eines Auftrags.
- **Abonnements** werden genutzt, indem das Programm des Anbieters selbst ausgeführt wird (Claude
  Code, Codex, Copilot, Antigravity). tarjim liest oder speichert niemals deren Anmeldedateien oder
  Tokens.
- **Der lokale Modus** hält die Medien auf dem Gerät: Die Modelle laden mit dem Hugging Face Hub im
  Offline-Modus, und das Netzwerk wird nur genutzt, während ein Werkzeug heruntergeladen wird, das
  die Person angefordert hat.
- **Downloads**: ffmpeg wird mit der SHA-256-Prüfsumme abgeglichen, die mit seinem Release
  veröffentlicht wurde.

## Bekannte Grenzen

- Wer auf Ihrem Computer Programme unter Ihrem Benutzerkonto ausführen kann, kann den Tresor und
  das Token lesen. tarjim schützt nicht vor einem kompromittierten Konto.
- Von Ihnen gewählte Cloud-Anbieter erhalten den Ton oder Text, den sie verarbeiten, zu ihren
  eigenen Bedingungen.

## Bekannte Probleme in Bibliotheken

Veröffentlichte Sicherheitslücken in Bibliotheken, die tarjim installiert und die noch keine getestete Version vermeiden kann: derzeit keine. Taucht eine auf, kommen ihre Angaben mit tarjim in `tarjim/known_issues.json`: **Einstellungen**, die `/update`-Antwort der Engine und `setup_status` der Chat-Werkzeuge zeigen sie auf den Computern, deren installierte Version betroffen ist, und sie verschwindet von selbst, sobald ein Update eine behobene Version installiert. CI schlägt bei jeder hier nicht aufgeführten Lücke fehl, und eine wöchentliche Prüfung meldet, wenn eine aufgeführte behoben werden kann.

**Geschlossen am 2026-10-23.** Sechs transformers-Meldungen (PYSEC-2025-217, PYSEC-2026-2288, PYSEC-2026-2289, PYSEC-2026-2290, PYSEC-2026-3929, PYSEC-2026-4174) blieben offen, solange qwen-asr, die damalige lokale Hör-Engine, transformers auf 4.57.6 festhielt. Das lokale Hören nutzt jetzt die eigenen Qwen3-ASR-Modelle von Transformers, daher installiert tarjim transformers 5.20.2 und qwen-asr nicht mehr; accelerate bleibt auf 1.15.0 (PYSEC-2026-3804 geschlossen), ohne Override.

**Was tarjim in jedem Fall tut.** Jedes Hugging-Face-Modell wird von einem festen Commit geladen (`tarjim/model_pins.py`), nur seine Einstellungen, Tokenizer, Chat-Vorlage und safetensors-Dateien, nie Code; seine großen Dateien müssen ihrem veröffentlichten SHA-256 entsprechen, und es wird aus diesem Ordner auf dem Computer geladen, mit dem Hub offline. `trust_remote_code` wird nie gesetzt, und das Paket `kernels` ist nicht installiert. Die Gewichte der Stimmtrennung laden nur, wenn sie demucs' eigene Modellklasse nennen, und das Vokalisierungsmodell nur, wenn beide Dateien dem SHA-256 ihres Releases entsprechen.
