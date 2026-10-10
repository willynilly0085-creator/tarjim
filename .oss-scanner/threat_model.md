# Threat model

## What this project does and where untrusted input enters

tarjim subtitles and dubs videos on the person's own computer. One Python process
(`tarjim-serve`, `tarjim/server/`) listens on `127.0.0.1:17653`, serves a web page, takes jobs from
a browser extension and from chat tools (an MCP server, `tarjim/assistant*.py`), and can poll the
person's own Telegram bot (`tarjim/phone/`). It runs as the person, with their files, and holds
their API keys in the operating system's vault.

Untrusted input, most exposed first:

1. **Any website the person has open.** A page can send requests to `127.0.0.1:17653` from the
   browser. The guard (`tarjim/server/guard.py`, `app.py`, `pairing.py`) must refuse everything
   without the token header or the page's own cookie on a same-origin request, refuse foreign
   `Host` headers (DNS rebinding), and let only a browser extension ask to pair.
2. **Links and media files.** A link is handed to yt-dlp (`tarjim/fetch.py`); a file, an upload or
   a Telegram attachment is handed to ffmpeg and ffprobe (`tarjim/media.py`, `tarjim/render/`).
   File names, titles, URLs and metadata come from strangers and end up in paths and in command
   arguments.
3. **Telegram.** Messages, file names, captions, callback data and links arrive from Telegram's
   servers (`tarjim/phone/`). Only the linked chat may give orders; everyone else must be ignored.
   Large files come over MTProto (`phone/large.py`).
4. **What an AI answers.** Transcripts and translations come from cloud or local models
   (`tarjim/engines/`, `tarjim/translate/`, `tarjim/listen/`), and the speech in a video is itself
   attacker-controlled text that reaches those models. Model output must only ever become subtitle
   text: never a path, a command, a setting or a tool call. It is written into SRT and ASS files
   (`tarjim/render/ass.py`), where ASS override tags are a way to inject.
5. **Downloads tarjim makes for itself.** ffmpeg (`tarjim/ffmpeg_setup.py`), vendor programs
   (`tarjim/engines/app_install.py`, `tarjim/installer.py`), model weights, and its own updates
   (`tarjim/update.py`, `server/update_routes.py`). An update replaces the running code.
6. **A chat assistant using the MCP tools.** The assistant may be steered by text it read
   elsewhere. The tools must never return a key or a token, never take one, and must not reach
   files outside tarjim's own folders.

## Components that matter most / least

Most:

- `tarjim/server/` — the guard, pairing, the routes that change settings or save keys, the routes
  that serve files (`safe_name`, the outputs of a job), uploads.
- `tarjim/vault.py`, `tarjim/keys.py`, `tarjim/config.py` — where secrets live and what is allowed
  to read them back. A key, the pairing token, the bot token or the Telegram session string
  appearing in any response, log line, error message or tool result is a finding.
- `tarjim/fetch.py`, `tarjim/media.py`, `tarjim/render/burn.py`, `tarjim/dub/` — every place a
  subprocess is started with something a stranger chose.
- `tarjim/phone/` — who may command the bot, and what a remote chat can make the computer do.
- `tarjim/update.py`, `tarjim/installer.py`, `tarjim/ffmpeg_setup.py`, `tarjim/autostart.py` —
  code that downloads, replaces or auto-starts programs.
- `tarjim/extension/` — the browser extension (context menus, `activeTab`, `scripting`), what it
  sends to the local server and what a web page can make it send.

Least:

- `tarjim/web/` and `i18n/` wording, `site/`, the tests, the rules that shape subtitle lines
  (`tarjim/segment.py`, `tarjim/rules.py`, `tarjim/qa.py`): correctness matters there, security
  rarely does.
- Third-party programs themselves (ffmpeg, yt-dlp, Claude Code, Codex, Ollama, the models) are out
  of scope; how tarjim calls them is in scope.

## How to exercise it

- `pytest -q` runs in the image without models or network. `tests/test_hardening.py`,
  `tests/test_silent_failures.py`, `tests/test_phone_*.py` and `tests/test_assistant_settings.py`
  show how the guard, the bot and the chat tools are driven in tests.
- `tarjim-serve` starts the server on `127.0.0.1:17653`; ffmpeg and ffprobe are installed
  (`TARJIM_FFMPEG`, `TARJIM_FFPROBE`). With no vault backend in the container, secrets fall back to
  the settings file under `~/.tarjim/`.
- No model weights are in the image, so a full job cannot run end to end; the code up to and after
  the models can.

## How we rate severity

- **Critical:** a website the person merely visits, a video or link they translate, a Telegram
  user who is not the linked chat, or an AI's answer leads to running code or commands on the
  computer, to reading or writing files outside tarjim's folders, or to a key or token leaving
  the computer. A way to make an update install code that did not come from the project's own
  release.
- **High:** the same outcomes when the person must first be tricked into one ordinary action
  (allowing a pairing request from the wrong extension, opening a crafted file). Any request from
  a web page that changes settings, starts jobs or reads results without the token. Reading
  another local user's secrets where the settings-file fallback is in use.
- **Medium:** a stranger can make tarjim fill the disk, hang forever or crash the server (denial
  of service); subtitle injection that changes how the video is drawn but runs nothing; leaking
  non-secret settings or file paths to a web page.
- **Low:** problems that need a program already running as the same user (it can read the vault
  and the token anyway; see SECURITY.md, "Known limits"), and hardening suggestions without a
  demonstrated effect.

## Anything to leave alone

- "A local program running as the same user can read the token or open the page": known and
  documented, not a finding.
- "Cloud providers receive the audio or text": that is the feature the person chose.
- The server speaks plain HTTP on the loopback address by design.
- Reports are most useful with the request, file or message that triggers the problem and the
  smallest patch that fits the code's limits (files 200 lines, functions 20 statements).
