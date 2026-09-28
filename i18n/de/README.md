# tarjim
<!-- languages -->
[English](../../README.md) · [العربية](../../i18n/ar/README.md) · [Español](../../i18n/es/README.md) · [Français](../../i18n/fr/README.md) · [Português](../../i18n/pt/README.md) · **Deutsch** · [Русский](../../i18n/ru/README.md) · [Türkçe](../../i18n/tr/README.md) · [हिन्दी](../../i18n/hi/README.md) · [اردو](../../i18n/ur/README.md) · [Bahasa Indonesia](../../i18n/id/README.md) · [日本語](../../i18n/ja/README.md) · [中文](../../i18n/zh/README.md) · [한국어](../../i18n/ko/README.md)

**Untertitel und Synchronisation für jedes Video, in Ihrer Sprache, auf Ihrem eigenen Computer.**

Link einfügen oder Datei ablegen. tarjim hört zu, setzt jede Zeile genau auf den Moment, in dem sie
gesprochen wird, hält die Sprecher auseinander, übersetzt in natürliche Sprache und brennt die
Untertitel ins Video ein, schreibt eine `.srt`-Datei oder synchronisiert das Video mit einer eigenen
Stimme für jeden Sprecher.

## Was es kann

- **Jede Quelle:** YouTube, X und andere Links (yt-dlp) oder jede Video- oder Audiodatei auf Ihrem
  Gerät.
- **34 Zielsprachen**, von rechts nach links wie von links nach rechts. Arabisch ist standardmäßig
  ein saudischer Dialekt; modernes Hocharabisch ist nur einen Klick entfernt.
- **Sorgfältiges Hören:** Der Ton wird dreimal abgehört und über jedes Wort wird abgestimmt, sodass
  ein einzelner Hörfehler nicht im Untertitel landet.
- **Exaktes Timing:** Die Wörter werden auf Ihrem Computer am Ton ausgerichtet (CTC Forced Alignment
  plus Sprachaktivitätserkennung). Untertitel laufen nie über einen Schnitt hinweg in die Einstellung
  der nächsten Person.
- **Sprecherbewusst:** Dialogzeilen mit Gedankenstrichen, eine Zeile pro Sprecher.
- **Synchronisation:** eine natürliche Gemini-Stimme pro Sprecher (nach Tonhöhe zugeordnet), ein
  lokaler Stimmklon jedes Sprechers (XTTS-v2), Studiostimmen oder Fish Audio. Ein separates
  Sprechskript schreibt Namen so, wie sie ausgesprochen werden, und Zahlen als Wörter, damit die
  Stimme sie richtig ausspricht.
- **Drei Nutzungswege:** ein Rechtsklick-Menü im Browser („ترجم للعربية“), eine lokale Webseite oder
  ein Chat: Fügen Sie tarjim zur Claude-App, zu Claude Code oder zu Codex hinzu und bitten Sie
  darum, einen Link zu übersetzen.

## Eine KI anbinden: drei Wege

| Weg | Optionen | Hinweise |
|---|---|---|
| API-Schlüssel | Gemini, OpenAI, Anthropic, OpenRouter, DeepSeek, Qwen, Mistral, Groq, xAI oder jede OpenAI-kompatible Adresse | Gemini und OpenAI können auch zuhören (Sprache zu Text). |
| Ihr Abonnement | Claude (über Claude Code), ChatGPT (über Codex), GitHub Copilot, Google AI (über Antigravity) | tarjim startet das Programm des Anbieters selbst mit Ihrer Anmeldung. Die Nutzung wird auf Ihren Tarif angerechnet, und es gelten die Bedingungen des jeweiligen Anbieters. |
| Auf Ihrem Computer | Ollama, LM Studio, Jan, llama.cpp, vLLM, KoboldCpp | Werden samt ihren Modellen automatisch erkannt. Nichts verlässt Ihr Gerät. |

Wählen Sie ein beliebiges Modell, das ein Anbieter bereitstellt. Wenn die gewählte Engine ausfällt
oder ihr Kontingent aufgebraucht ist, weicht tarjim auf die lokale Engine aus, sofern eine
verfügbar ist.

## Installation mit Ihrer KI (ein Schritt)

In Claude Code:

```bash
claude plugin marketplace add willynilly0085-creator/tarjim
claude plugin install tarjim@tarjim
```

Sagen Sie Ihrer KI dann „richte tarjim ein“. Sie installiert die Engine im Hintergrund (die
Grafikkarten-Version, wenn Sie eine NVIDIA-Karte haben), startet sie ohne sichtbares Fenster und
öffnet die Einrichtungsseite. Von da an verwendet Ihre KI die Werkzeuge von tarjim direkt:
„übersetze diesen Link ins Französische und brenne die Untertitel ein“, „nutze mein
Claude-Abonnement für die Übersetzung“, „wechsle zum lokalen Modell“. tarjim ist ein Werkzeug, das
Ihre KI bedient, kein weiterer Assistent, mit dem Sie sich unterhalten. Das Plugin benötigt
[uv](https://docs.astral.sh/uv/).

Andere MCP-Apps (Codex, Cursor und weitere): Fügen Sie nach der Installation der Engine den Befehl
`tarjim-mcp` als MCP-Server hinzu, zum Beispiel `codex mcp add tarjim -- tarjim-mcp`. Codex bittet
bei jedem Werkzeugaufruf um Ihre Zustimmung; damit die Werkzeuge von tarjim ohne Nachfrage laufen,
fügen Sie `default_tools_approval_mode = "approve"` unter `[mcp_servers.tarjim]` in
`~/.codex/config.toml` hinzu.

Getestet: Eine Claude-Code-Sitzung mit dem Plugin las die Einstellungen, legte das Glossar fest,
übersetzte einen YouTube-Link ins Spanische und lieferte die Untertitel zurück; Codex (ChatGPT-Tarif)
las die Einstellungen und legte das Glossar fest. Die ChatGPT-Website und die Desktop-App können
Werkzeuge auf Ihrem Computer noch nicht erreichen (sie akzeptieren nur entfernte MCP-Server);
verwenden Sie für ChatGPT daher Codex.

## Manuelle Installation (Windows)

Benötigt Python 3.11 und etwa 10 GB Speicherplatz für die lokalen Modelle.

```powershell
git clone https://github.com/willynilly0085-creator/tarjim
cd tarjim
python -m venv .venv
# NVIDIA graphics card: install the CUDA build of PyTorch first (the default one is CPU only)
.venv\Scripts\python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python -m pip install -e ".[dub]"
.venv\Scripts\tarjim-serve
```

Öffnen Sie <http://127.0.0.1:17653>. Die Einrichtungsseite prüft Ihr Gerät, bindet eine KI an und
lädt herunter, was Sie brauchen, einschließlich ffmpeg (unter Windows wird es heruntergeladen und
mit seiner veröffentlichten SHA-256-Prüfsumme abgeglichen). Ohne nutzbare Grafikkarte funktioniert
alles weiterhin auf dem Prozessor, nur langsamer.

**macOS und Linux** folgen denselben Schritten mit `.venv/bin/...`, dazu `brew install ffmpeg` oder
`sudo apt install ffmpeg`. Diese Plattformen wurden noch nicht getestet.

### Browser-Erweiterung

tarjim lebt in Ihrem Browser: Klicken Sie mit der rechten Maustaste auf ein Video oder einen Link,
wählen Sie **ترجم للعربية** (oder Ihre Sprache) und dann Untertitel, eingebrannte Untertitel oder
Synchronisation. Das Popup zeigt den Stand jedes Auftrags und lässt Sie ihn pausieren, abbrechen
oder das Ergebnis öffnen.

Öffnen Sie in Chrome `chrome://extensions`, schalten Sie Developer mode (Entwicklermodus) ein,
wählen Sie **Load unpacked** (Entpackte Erweiterung laden) und dann den Ordner `extension`. Die
Erweiterung koppelt sich selbst: Drücken Sie auf der tarjim-Seite **Allow** (Zulassen).

### Chat

Drücken Sie auf der Einrichtungsseite im Schritt „Use tarjim from a chat“ (tarjim aus einem Chat
nutzen) neben der Claude-App, Claude Code oder Codex auf **Add** (Hinzufügen). Ihre KI kann dann
das gesamte Werkzeug für Sie bedienen:

- „Übersetze diesen Link ins Arabische und synchronisiere ihn“, „in welcher Phase ist er?“,
  „pausiere ihn“, „öffne das Ergebnis“;
- die Einstellungen ändern: „nutze mein Claude-Abonnement für die Übersetzung“, „wechsle zum lokalen
  Modell“, „liste die KIs auf, die ich anbinden kann“, „stelle die Oberfläche auf Englisch um“;
- Ihnen die fertigen Untertitel vorlesen, einen fehlgeschlagenen Auftrag wiederholen oder ein
  fehlendes Werkzeug herunterladen.

Schlüssel werden nie über den Chat eingegeben; die KI öffnet dafür die tarjim-Seite.

### Kommandozeile

```bash
tarjim video.mp4                 # Arabic (Saudi), burned into the video
tarjim video.mp4 --to fr         # any target language
tarjim video.mp4 --no-burn       # .srt and .ass only
```

## Datenschutz und Sicherheit

- **Schlüssel** werden im verschlüsselten Tresor Ihres Betriebssystems gespeichert (Windows
  Credential Manager, macOS Keychain, Secret Service). Die Einstellungsdatei enthält keine.
- **Was Ihr Gerät verlässt**, hängt davon ab, wie Sie verbinden: Der Ton des Clips geht an den von
  Ihnen gewählten Anbieter für die Spracherkennung, der Text an die von Ihnen gewählten Anbieter für
  Übersetzung und Stimme. Im lokalen Modus verlässt nichts das Gerät: Das wurde gemessen, indem
  während eines vollständigen lokalen Auftrags einschließlich Synchronisation jede Verbindung
  beobachtet wurde (null externe Verbindungen). Die Modelle laden offline; das Internet wird nur
  genutzt, wenn Sie ein Werkzeug herunterladen.
- **Der lokale Server** lauscht nur auf 127.0.0.1. Jede Anfrage benötigt ein Token oder das
  Same-Site-Cookie der Seite, fremde `Host`-Header werden abgewiesen (DNS-Rebinding), Websites
  können ihn weder erreichen noch eine Kopplung anfordern, und er liefert keine Datei außerhalb
  seiner eigenen Ordner aus.

Um ein Problem zu melden, siehe [SECURITY.md](SECURITY.md).

## Modelllizenzen

Der Code von tarjim enthält keine Modellgewichte; Sie laden sie bei ihren Eigentümern herunter.
Einige davon sind **nicht für die kommerzielle Nutzung lizenziert**:

| Werkzeug | Lizenz | Kommerzielle Nutzung |
|---|---|---|
| Timing-Aligner `MahmoudAshraf/mms-300m-1130-forced-aligner` (erforderlich) | CC-BY-NC-4.0 | Nein |
| Stimmklon XTTS-v2 (optional, fragt nach Einwilligung) | Coqui Public Model License | Nein |
| Lokale Übersetzung `aya-expanse:8b` (optional) | CC-BY-NC-4.0 | Nein |
| Lokale Spracherkennung Qwen3-ASR-1.7B und Qwen3-ForcedAligner | Apache-2.0 | Ja |
| ffmpeg (LGPL-Build) | LGPL-2.1 | Ja |

Die Einrichtungsseite zeigt jede Lizenz neben dem zugehörigen Download an.

## Stand

Getestet unter Windows 11 mit einer RTX 5080 sowie mit einer Neuinstallation ohne
Grafikunterstützung: Links und Dateien, eingebrannte Untertitel und `.srt`, Französisch und
Arabisch, Pausieren, Fortsetzen, Abbrechen und Wiederholen, die drei Anbindungswege (Claude- und
ChatGPT-Abonnements, lokales Ollama), die Chat-Werkzeuge und die oben genannten
Sicherheitsprüfungen. Noch nicht getestet: macOS, Linux sowie Abonnements von GitHub Copilot und
Antigravity.

## Lizenz

Jeder darf tarjim frei nutzen, untersuchen, verändern und weitergeben, zu jedem Zweck **außer zur
kommerziellen Nutzung**: Niemand darf es verkaufen oder einen darauf aufbauenden Dienst verkaufen.
Siehe [LICENSE.md](LICENSE.md) (PolyForm Noncommercial 1.0.0); der vollständige, rechtsverbindliche
Text steht in [../../LICENSE.md](../../LICENSE.md). Das entspricht den nicht-kommerziellen Lizenzen
der verwendeten Modelle.

## Entwicklung

```bash
pip install -e ".[dub,dev]"
pytest && ruff check tarjim tests && mypy tarjim
```

Designentscheidungen und Messungen sind in [docs/decisions.md](../../docs/decisions.md)
festgehalten. Siehe [CONTRIBUTING.md](CONTRIBUTING.md).
