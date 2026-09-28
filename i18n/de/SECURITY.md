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
