# tarjim
<!-- languages -->
[English](../../README.md) · [العربية](../../i18n/ar/README.md) · [Español](../../i18n/es/README.md) · [Français](../../i18n/fr/README.md) · [Português](../../i18n/pt/README.md) · **Deutsch** · [Русский](../../i18n/ru/README.md) · [Türkçe](../../i18n/tr/README.md) · [हिन्दी](../../i18n/hi/README.md) · [اردو](../../i18n/ur/README.md) · [Bahasa Indonesia](../../i18n/id/README.md) · [日本語](../../i18n/ja/README.md) · [中文](../../i18n/zh/README.md) · [한국어](../../i18n/ko/README.md)

Entwickelt von [Indicators](https://indicators.sa/) · [indicators.sa](https://indicators.sa/)

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
  lokaler Stimmklon jedes Sprechers (VoxCPM2), Studiostimmen oder Fish Audio. Ein separates
  Sprechskript schreibt Namen so, wie sie ausgesprochen werden, und Zahlen als Wörter, damit die
  Stimme sie richtig ausspricht.
- **Drei Nutzungswege:** ein Rechtsklick-Menü im Browser („ترجم للعربية“), eine lokale Webseite oder
  ein Chat: Fügen Sie tarjim zur Claude-App, zu Claude Code oder zu Codex hinzu und bitten Sie
  darum, einen Link zu übersetzen.
- **Das tarjim-Zeichen:** Videos von tarjim tragen sein kleines Logo und @Cut_Code in einer Ecke,
  abseits der Untertitel (`.srt`- und `.ass`-Dateien nicht); in den Einstellungen abschaltbar.

## Eine KI anbinden: drei Wege

| Weg | Optionen | Hinweise |
|---|---|---|
| API-Schlüssel | Gemini, OpenAI, Anthropic, OpenRouter, DeepSeek, Qwen, Mistral, Groq, xAI oder jede OpenAI-kompatible Adresse | Gemini und OpenAI können auch zuhören (Sprache zu Text). |
| Ihr Abonnement | Claude (über Claude Code), ChatGPT (über Codex), Grok (über Grok Build), GitHub Copilot, Google AI (über Antigravity) | tarjim startet das Programm des Anbieters selbst mit Ihrer Anmeldung. Die Nutzung wird auf Ihren Tarif angerechnet, und es gelten die Bedingungen des jeweiligen Anbieters. |
| Auf Ihrem Computer | Ollama, LM Studio, Jan, llama.cpp, vLLM, KoboldCpp | Werden samt ihren Modellen automatisch erkannt. Nichts verlässt Ihr Gerät. |

Wählen Sie ein beliebiges Modell, das ein Anbieter bereitstellt. Wenn die gewählte Engine ausfällt
oder ihr Kontingent aufgebraucht ist, weicht tarjim auf die lokale Engine aus, sofern eine
verfügbar ist.

## Was Ihr Computer braucht

Die aufwendigen Teile sind optional. Was Sie brauchen, hängt davon ab, welche Teile auf Ihrem
eigenen Computer laufen:

| Was Sie nutzen | Grafikkarte | Arbeitsspeicher (RAM) | Freier Speicherplatz |
|---|---|---|---|
| Untertitel mit einer KI, die Sie anbinden (ein Gemini-Schlüssel, ein Claude- oder ChatGPT-Abonnement, jeder API-Schlüssel) | Nicht nötig | 8 GB | etwa 6 GB |
| Synchronisation mit natürlichen oder Studiostimmen | Nicht nötig | 8 GB | nichts zusätzlich |
| Zuhören auf diesem Computer (der Ton verlässt ihn nie) | NVIDIA, 8 GB | 16 GB | 5.9 GB mehr |
| Übersetzen auf diesem Computer (Ollama mit aya-expanse 8B) | 8 GB | 16 GB | 5.1 GB mehr |
| Synchronisation mit der eigenen Stimme jedes Sprechers | NVIDIA, 8 GB | 16 GB | 4.7 GB mehr |

- **System:** Windows 10 oder 11, 64 Bit. macOS und Linux führen denselben Code aus, wurden aber
  noch nicht getestet.
- **Internet:** für die Downloads und für die KI, die Sie anbinden. Wenn Zuhören und Übersetzen auf
  diesem Computer laufen, arbeiten die Aufträge offline, sobald alles heruntergeladen ist.
- **Ohne NVIDIA-Karte** funktioniert trotzdem alles auf dem Prozessor, nur deutlich langsamer; die
  Synchronisation mit der eigenen Stimme des Sprechers ist dort nicht praktikabel.
- **Ein Modell nach dem anderen:** tarjim gibt jedes Modell frei, bevor das nächste geladen wird.
  Die Grafikkarte braucht daher Platz für das größte (etwa 6 GB), nicht für alle zusammen.
- **Alles auf diesem Computer:** etwa 22 GB Speicherplatz.

Gemessen unter Windows 11 mit einer RTX 5080 (16 GB) und 32 GB RAM: Das Zuhören auf der Karte
erreichte höchstens 6.8 GB Grafikspeicher, das Übersetzen mit aya-expanse 8B 5.7 GB und die eigene
Stimme des Sprechers 6.1 GB, bei etwa 3 Sekunden pro Satz. Beim Laden des Modells für die
Sprecherstimme werden kurzzeitig etwa 11 GB RAM belegt, bevor es sich bei 2.5 GB einpendelt; deshalb
werden 16 GB verlangt. Die Engine selbst (Python mit der Grafikkarten-Variante von PyTorch) belegt
etwa 4 GB der oben genannten Speicherplatzwerte.

## Installation unter Windows (eine Datei)

Sie müssen vorher nichts installiert haben: kein Python, kein KI-Werkzeug, kein Terminal.

1. Drücken Sie auf dieser Seite **Code**, dann **Download ZIP**, und entpacken Sie die Datei.
2. Öffnen Sie den Ordner und doppelklicken Sie auf **install** (`install.cmd`). Fragt Windows, ob
   die Datei ausgeführt werden soll, erlauben Sie es (**Run**, oder **More info** und dann
   **Run anyway**).
3. Lassen Sie das Fenster offen, bis „Ready“ erscheint. Danach öffnet sich die Seite von tarjim in
   Ihrem Browser, und die Einrichtung geht dort weiter: Ihre Sprache, die KI, die Sie verwenden
   möchten, und die Browser-Erweiterung.

Danach läuft tarjim im Hintergrund ohne Fenster und startet mit dem Computer. Eine Verknüpfung
**tarjim** auf dem Desktop und im Startmenü öffnet die Seite und startet tarjim vorher, falls es
nicht läuft.

### Was die Datei macht und was sie herunterlädt

Sie lädt einmalig etwa 4 GB herunter. tarjim selbst ist kleiner als 2 MB; der Rest ist das, worauf
es läuft.

| Was installiert wird | Größe | Wozu |
|---|---|---|
| uv, ein kleines Installationswerkzeug | 33 MB | Bringt Python und die Bibliotheken in den eigenen Ordner von tarjim, damit nichts sonst auf dem Computer angetastet wird |
| Python 3.12, falls der Computer keines hat | klein | tarjim ist in Python geschrieben und bekommt seine eigene Kopie |
| PyTorch | 2.8 GB mit NVIDIA-Karte, ohne Karte kleiner | Führt das Modell aus, das jedes Wort im Moment des Sprechens platziert und das jeder Auftrag braucht, sowie die Modelle für Zuhören und Stimme, wenn Sie sie auf diesem Computer laufen lassen |
| Etwa 160 weitere Bibliotheken | etwa 1 GB | Ein Video von einem Link herunterladen, mit der angebundenen KI sprechen, Zuhören, Synchronisation, der Telefon-Bot |

Anschließend startet die Datei tarjim, trägt es bei den Programmen ein, die mit Windows starten,
legt die Verknüpfung auf dem Desktop ab und öffnet die Seite. Sie ändert sonst nichts und braucht
keine Administratorrechte.

Die Einrichtungsseite lädt den Rest herunter, und zwar nur, was Ihre Auswahl braucht:

| Von der Einrichtung geladen | Größe | Wann |
|---|---|---|
| Das Timing-Modell | 1.2 GB | Immer |
| ffmpeg | 80 MB | Immer (es liest das Video und brennt die Untertitel ein) |
| Das Modell fürs Zuhören | 5.9 GB | Nur, wenn Sie das Zuhören auf diesem Computer wählen |
| Das Modell für die Sprecherstimme | 4.7 GB | Nur, wenn Sie mit der eigenen Stimme jedes Sprechers synchronisieren |

Mit einer Cloud-KI (ein Gemini-Schlüssel oder ein Gemini-, Claude-, ChatGPT- oder Grok-Abonnement)
sind nur die ersten beiden nötig: Auf Ihrem Computer läuft keine KI.

So entfernen Sie tarjim: Führen Sie `uv tool uninstall tarjim` aus und löschen Sie dann den Ordner
`.tarjim` in Ihrem Benutzerordner und die Verknüpfung.

Getestet, indem die Datei auf einem Computer ohne uv ausgeführt wurde: Sie installierte uv und
tarjim und startete die Engine. Windows 10 haben wir nicht getestet.

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

Benötigt Python 3.12. Speicherplatz, Arbeitsspeicher und Grafikkarte: siehe [Was Ihr Computer braucht](#was-ihr-computer-braucht).

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
wählen Sie **Load unpacked** (Entpackte Erweiterung laden) und dann den Ordner `~/.tarjim/extension`. Die
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

### Handy

Schicken Sie von einem beliebigen Handy, iPhone oder Android, zu Hause oder unterwegs, einen
Videolink an Ihren eigenen Telegram-Bot, und das übersetzte Video kommt im selben Chat zurück.
Öffnen Sie in den Einstellungen **Handy**: Erstellen Sie in BotFather einen Bot (`/newbot`),
fügen Sie dessen Token ein (es bleibt im Tresor Ihres Computers), scannen Sie dann den QR-Code
mit Ihrem Handy und tippen Sie auf **Starten**. Der Bot antwortet nur Ihrem Konto, und Ihr
Computer fragt bei Telegram selbst nach neuen Nachrichten, sodass kein Port zum Internet
geöffnet wird. Sprache, Ergebnis und Stil kommen aus den Einstellungen; mit `/mode` im Bot
ändern Sie das Ergebnis. Telegram erlaubt Bots, Videos bis 20 MB herunterzuladen und Dateien bis
50 MB zu senden: Ein größeres Ergebnis wird passend neu kodiert, oder Sie erhalten die
Untertiteldatei, und das vollständige Video bleibt auf Ihrem Computer. Der Bot antwortet,
solange Ihr Computer und tarjim laufen.

### Kommandozeile

```bash
tarjim video.mp4                 # Arabic (Saudi), burned into the video
tarjim video.mp4 --to fr         # any target language
tarjim video.mp4 --no-burn       # .srt and .ass only
```

## Updates

tarjim hält sich selbst aktuell. Einmal am Tag fragt die Engine bei GitHub nach der Nummer der
neuesten Version: eine einzige Anfrage, die nichts über Sie oder Ihre Videos enthält. Ist **tarjim
automatisch aktualisieren** eingeschaltet (wird bei der Einrichtung angeboten und lässt sich in den
Einstellungen ändern), wird eine neuere Version im Hintergrund installiert, solange kein Auftrag
läuft, und tarjim startet nach wenigen Minuten von selbst wieder; die Browser-Erweiterung lädt sich
passend dazu neu. Ist die Option ausgeschaltet, zeigt die Seite einen Hinweis und die Schaltfläche
**Jetzt aktualisieren**. Eine Kopie, die Sie aus dem Quellcode ausführen, aktualisieren Sie mit
`git pull`.

### Wie seine Bestandteile aktuell bleiben

- **yt-dlp**, der Teil, der von Videoseiten herunterlädt, aktualisiert sich selbst: Die Seiten
  ändern sich alle paar Wochen, und eine alte Version lädt dort nicht mehr. Einmal am Tag fragt die
  Engine bei PyPI nach der neuesten Version (eine Anfrage, nichts über Sie) und installiert eine
  neuere, solange nichts heruntergeladen wird.
- **Alle anderen Bibliotheken** werden in der Version installiert, die mit Ihrer tarjim-Version
  getestet wurde, und ändern sich erst mit der nächsten Version. Jede Woche werden neuere Versionen
  getestet und auf bekannte Schwachstellen geprüft, bevor eine Version sie übernimmt. PyTorch folgt
  dem Build, den uv für Ihre Grafikkarte wählt.

Wenn Sie **tarjim automatisch aktualisieren** ausschalten, stoppt beides. Eine Kopie aus dem
Quellcode erhält die getesteten Versionen mit `uv pip install -c tarjim/constraints.txt --overrides tarjim/overrides.txt -e ".[dub]"`.

### Bekannte Probleme in Bibliotheken

Derzeit keine: Keine Bibliothek, die tarjim installiert, hat eine veröffentlichte Sicherheitslücke, die ihre getesteten Versionen nicht vermeiden. Die sechs transformers-Probleme, die bis 2026-10-23 aufgeführt waren, sind behoben, denn das lokale Hören nutzt jetzt die eigenen Qwen3-ASR-Modelle von Transformers. Taucht eines auf, zeigt **Einstellungen** es auf den betroffenen Computern, und der Hinweis verschwindet von selbst, sobald ein Update eine behobene Version installiert. Details stehen in [SECURITY.md](SECURITY.md).

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
| Stimmklon VoxCPM2 (optional) | Apache-2.0 | Ja |
| Lokale Übersetzung `aya-expanse:8b` (optional) | CC-BY-NC-4.0 | Nein |
| Lokale Spracherkennung Qwen3-ASR-1.7B und Qwen3-ForcedAligner | Apache-2.0 | Ja |
| ffmpeg (LGPL-Build) | LGPL-2.1 | Ja |

Die Einrichtungsseite zeigt jede Lizenz neben dem zugehörigen Download an.

## Stand

Getestet unter Windows 11 mit einer RTX 5080 sowie mit einer Neuinstallation ohne
Grafikunterstützung: Links und Dateien, eingebrannte Untertitel und `.srt`, Französisch und
Arabisch, Pausieren, Fortsetzen, Abbrechen und Wiederholen, die drei Anbindungswege (Claude- und
ChatGPT-Abonnements, lokales Ollama), die Chat-Werkzeuge, die Synchronisation mit der eigenen
Stimme des Sprechers (Englisch in saudisches Arabisch) und die oben genannten
Sicherheitsprüfungen. Noch nicht getestet: macOS, Linux, Abonnements von GitHub Copilot und
Antigravity sowie der Handy-Bot mit dem echten Telegram-Dienst (sein Code ist durch Tests mit
einem simulierten Telegram abgedeckt).

## Lizenz

tarjim ist für alle kostenlos, auch für Unternehmen: Sie dürfen es nutzen, untersuchen, verändern
und weitergeben, zu jedem Zweck. Nur eines ist nicht erlaubt: **es zu verkaufen**. Niemand darf
tarjim verkaufen oder ein Produkt oder eine Dienstleistung verkaufen, deren Wert aus tarjim stammt
(auch Hosting und kostenpflichtiger Support). Siehe [LICENSE.md](LICENSE.md) (Apache License 2.0
mit Commons Clause); der vollständige, rechtsverbindliche Text steht in [LICENSE](../../LICENSE).

Die Modelle, die tarjim herunterlädt, haben eigene Lizenzen, und einige davon verbieten die
kommerzielle Nutzung: Prüfen Sie die Tabelle der Modelllizenzen oben, bevor Sie diese Modelle
beruflich einsetzen.

## Entwicklung

```bash
pip install -e ".[dub,dev]"
pytest && ruff check tarjim tests && mypy tarjim
```

Designentscheidungen und Messungen sind in [docs/decisions.md](../../docs/decisions.md)
festgehalten. Siehe [CONTRIBUTING.md](CONTRIBUTING.md).
