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

Veröffentlichte Sicherheitslücken in Bibliotheken, die tarjim installiert, und die noch keine getestete Version vermeiden kann, weil qwen-asr (die lokale Hör-Engine) genau transformers 4.57.6 verlangt und mit jeder Version 5 nicht mehr läuft. Die Art, wie tarjim die Bibliothek nutzt, erreicht keine davon: Jedes Modell von Hugging Face wird aus einer festen, von tarjim geprüften Version geladen, nur mit Einstellungs- und Gewichtsdateien (nie Code), und offline aus seinem Ordner auf dem Computer genutzt. Die Einstellungen zeigen die, die auf deinem Computer zutreffen, und jede verschwindet von selbst, sobald ein Update eine behobene Version installiert.

| Hinweis | Bibliothek | Betroffene Versionen | Behoben in |
|---|---|---|---|
| PYSEC-2025-217 | transformers | `<=5.0.0rc0` | 5.0.0 |
| PYSEC-2026-2288 | transformers | `<5.0.0` | 5.0.0 |
| PYSEC-2026-2289 | transformers | `<5.3.0` | 5.3.0 |
| PYSEC-2026-2290 | transformers | `<5.5.0` | 5.5.0 |
| PYSEC-2026-3929 | transformers | `<5.10.0` | 5.10.0 |
| PYSEC-2026-4174 | transformers | `>=4.49.0,<=5.8.1` | 5.9.0 |

Details (auf Englisch): [SECURITY.md](../../SECURITY.md#known-library-issues).
