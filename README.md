# tarjim

**Subtitles and dubbing for any video, in your language, on your own computer.**
<!-- languages -->
**English** · [العربية](i18n/ar/README.md) · [Español](i18n/es/README.md) · [Français](i18n/fr/README.md) · [Português](i18n/pt/README.md) · [Deutsch](i18n/de/README.md) · [Русский](i18n/ru/README.md) · [Türkçe](i18n/tr/README.md) · [हिन्दी](i18n/hi/README.md) · [اردو](i18n/ur/README.md) · [Bahasa Indonesia](i18n/id/README.md) · [日本語](i18n/ja/README.md) · [中文](i18n/zh/README.md) · [한국어](i18n/ko/README.md)

Paste a link or drop a file. tarjim listens, times every line to the moment it is spoken, keeps
each speaker apart, translates into natural speech, and burns the subtitles into the video, writes
an `.srt`, or dubs it with a voice for every speaker.

## What it does

- **Any source:** YouTube, X and other links (yt-dlp), or any video or audio file on your device.
- **34 target languages**, right-to-left and left-to-right. Arabic defaults to a Saudi dialect;
  Modern Standard Arabic is one click away.
- **Careful listening:** the audio is heard three times and every word is voted on, so a single
  mishearing does not reach the subtitle.
- **Exact timing:** words are aligned to the audio on your computer (CTC forced alignment plus
  voice-activity detection). Subtitles never run across a shot cut into the next person's shot.
- **Speaker aware:** dialogue lines with dashes, one line per speaker.
- **Dubbing:** a natural Gemini voice per speaker (matched by pitch), a local voice clone of each
  speaker (VoxCPM2), studio voices, or Fish Audio. A separate voice script writes names as they
  are pronounced and numbers as words, so the voice says them correctly.
- **Three ways to use it:** a right-click menu in the browser ("ترجم للعربية"), a local web page,
  or a chat: add tarjim to the Claude app, Claude Code or Codex and ask it to translate a link.

## Connect an AI: three ways

| Way | Choices | Notes |
|---|---|---|
| API key | Gemini, OpenAI, Anthropic, OpenRouter, DeepSeek, Qwen, Mistral, Groq, xAI, or any OpenAI-compatible address | Gemini and OpenAI can also listen (speech to text). |
| Your subscription | Claude (through Claude Code), ChatGPT (through Codex), GitHub Copilot, Google AI (through Antigravity) | tarjim runs the vendor's own program with your sign-in. Usage counts against your plan and each vendor's terms apply. |
| On your computer | Ollama, LM Studio, Jan, llama.cpp, vLLM, KoboldCpp | Found automatically with their models. Nothing leaves your device. |

Pick any model a provider offers. If the chosen engine fails or runs out of quota, tarjim falls
back to the local engine when one is available.

## What your computer needs

The heavy parts are optional. What you need depends on which parts run on your own computer:

| What you use | Graphics card | Memory (RAM) | Free disk |
|---|---|---|---|
| Subtitles with an AI you connect (a Gemini key, a Claude or ChatGPT subscription, any API key) | Not needed | 8 GB | about 6 GB |
| Dubbing with natural or studio voices | Not needed | 8 GB | nothing extra |
| Listening on this computer (the audio never leaves it) | NVIDIA, 8 GB | 16 GB | 6.3 GB more |
| Translating on this computer (Ollama with aya-expanse 8B) | 8 GB | 16 GB | 5.1 GB more |
| Dubbing in each speaker's own voice | NVIDIA, 8 GB | 16 GB | 4.7 GB more |

- **System:** Windows 10 or 11, 64-bit. macOS and Linux run the same code but have not been tested yet.
- **Internet:** for the downloads and for the AI you connect. With listening and translating on
  this computer, jobs run offline once everything is downloaded.
- **Without an NVIDIA card** everything still works on the processor, only much slower; dubbing in
  the speaker's own voice is not practical there.
- **One model at a time:** tarjim frees each model before the next one loads, so the graphics card
  needs room for the largest one (about 6 GB), not for all of them together.
- **Everything on this computer:** about 22 GB of disk.

Measured on Windows 11 with an RTX 5080 (16 GB) and 32 GB of RAM: listening on the card peaked at
5.9 GB of graphics memory, translating with aya-expanse 8B at 5.7 GB and the speaker's own voice at
6.1 GB, about 3 seconds per sentence. Loading the speaker-voice model briefly takes about 11 GB of
RAM before settling at 2.5 GB, which is why it asks for 16 GB. The engine itself (Python with the
graphics-card build of PyTorch) takes about 4 GB of the disk figures above.

## Install with your AI (one step)

In Claude Code:

```bash
claude plugin marketplace add willynilly0085-creator/tarjim
claude plugin install tarjim@tarjim
```

Then tell your AI "set up tarjim". It installs the engine in the background (the graphics-card
build when you have an NVIDIA card), starts it without any window and opens the setup page. From
then on your AI uses tarjim's tools directly: "translate this link into French and burn the
subtitles", "use my Claude subscription for translation", "switch to the local model". tarjim is a
tool your AI operates, not another assistant to talk to. The plugin needs
[uv](https://docs.astral.sh/uv/).

Other MCP apps (Codex, Cursor, and more): after the engine is installed, add the command
`tarjim-mcp` as an MCP server, for example `codex mcp add tarjim -- tarjim-mcp`. Codex asks you to
approve each tool call; to let tarjim's tools run without asking, add
`default_tools_approval_mode = "approve"` under `[mcp_servers.tarjim]` in `~/.codex/config.toml`.

Tested: a Claude Code session with the plugin read the settings, set the glossary, translated a
YouTube link into Spanish and returned the subtitles; Codex (ChatGPT plan) read the settings and set
the glossary. The ChatGPT website and desktop app cannot reach tools on your computer yet (they
only accept remote MCP servers), so use Codex for ChatGPT.

## Install by hand (Windows)

Needs Python 3.11. Disk, memory and graphics card: see
[What your computer needs](#what-your-computer-needs).

```powershell
git clone https://github.com/willynilly0085-creator/tarjim
cd tarjim
python -m venv .venv
# NVIDIA graphics card: install the CUDA build of PyTorch first (the default one is CPU only)
.venv\Scripts\python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python -m pip install -e ".[dub]"
.venv\Scripts\tarjim-serve
```

Open <http://127.0.0.1:17653>. The setup page checks your device, connects an AI, and downloads
what you need, including ffmpeg (on Windows it is downloaded and checked against its published
SHA-256). Without a usable graphics card everything still works on the processor, only slower.

**macOS and Linux** follow the same steps with `.venv/bin/...`, plus `brew install ffmpeg` or
`sudo apt install ffmpeg`. These platforms have not been tested yet.

### Browser extension

tarjim lives in your browser: right-click any video or link and choose **ترجم للعربية** (or your
language), then pick subtitles, burned-in subtitles or dubbing. The popup shows every job's stage
and lets you pause, cancel or open the result.

In Chrome open `chrome://extensions`, turn on Developer mode, choose **Load unpacked** and pick the
`~/.tarjim/extension` folder. The extension pairs itself: press **Allow** on the tarjim page.

### Chat

On the setup page, step "Use tarjim from a chat", press **Add** next to the Claude app, Claude Code
or Codex. Your AI can then run the whole tool for you:

- "Translate this link into Arabic and dub it", "what stage is it at?", "pause it", "open the result";
- change the settings: "use my Claude subscription for translation", "switch to the local model",
  "list the AIs I can connect", "make the interface English";
- read the finished subtitles back to you, retry a failed job, or download a missing tool.

Keys are never entered through chat; the AI opens the tarjim page for that.

### Phone

Send a video link to your own Telegram bot from any phone, iPhone or Android, at home or away, and
the translated video comes back in the same chat. In Settings, open **Phone**: make a bot in
BotFather (`/newbot`), paste its token (it stays in your computer's vault), then scan the QR code
with your phone and press Start. The bot answers your account only, and your computer asks
Telegram for new messages, so no port is opened to the internet. The language, result and style
come from Settings; `/mode` in the bot changes the result. Telegram lets bots download videos up to
20 MB and send files up to 50 MB: a larger result is re-encoded to fit, or you get the subtitle
file and the full video stays on your computer. The bot answers while your computer and tarjim are
running.

### Command line

```bash
tarjim video.mp4                 # Arabic (Saudi), burned into the video
tarjim video.mp4 --to fr         # any target language
tarjim video.mp4 --no-burn       # .srt and .ass only
```

## Privacy and security

- **Keys** are stored in your operating system's encrypted vault (Windows Credential Manager,
  macOS Keychain, Secret Service). The settings file holds none.
- **What leaves your device** depends on the way you connect: the audio of the clip goes to the
  listening provider you chose, and the text goes to the translation and voice providers you chose.
  In local mode nothing leaves: this was measured by watching every connection during a full local
  job, dubbing included (zero external connections). Models load offline; the internet is used only
  when you download a tool.
- **The local server** listens on 127.0.0.1 only. Every request needs a token or the page's
  same-site cookie, foreign `Host` headers are refused (DNS rebinding), websites cannot reach it or
  ask to pair, and it serves no file outside its own folders.

See [SECURITY.md](SECURITY.md) to report a problem.

## Model licenses

tarjim's code does not include model weights; you download them from their owners. Some of them
are **not licensed for commercial use**:

| Tool | License | Commercial use |
|---|---|---|
| Timing aligner `MahmoudAshraf/mms-300m-1130-forced-aligner` (required) | CC-BY-NC-4.0 | No |
| Voice clone VoxCPM2 (optional) | Apache-2.0 | Yes |
| Local translation `aya-expanse:8b` (optional) | CC-BY-NC-4.0 | No |
| Local listening Qwen3-ASR-1.7B and Qwen3-ForcedAligner | Apache-2.0 | Yes |
| ffmpeg (LGPL build) | LGPL-2.1 | Yes |

The setup page shows each license next to its download.

## Status

Tested on Windows 11 with an RTX 5080, and from a clean install with no graphics support: links and
files, burned subtitles and `.srt`, French and Arabic, pause, resume, cancel and retry, the three
ways to connect (Claude and ChatGPT subscriptions, local Ollama), the chat tools, dubbing in the
speaker's own voice (English into Saudi Arabic) and the security checks above. Not tested yet:
macOS, Linux, GitHub Copilot and Antigravity subscriptions, and the phone bot against the live
Telegram service (its code is covered by tests with a simulated Telegram).

## License

tarjim is free for everyone, companies included: use it, study it, change it and share it, for any
purpose. The one thing not allowed is **selling it**: nobody may sell tarjim, or sell a product or
service (hosting and paid support included) whose value comes from tarjim. See [LICENSE](LICENSE)
(Apache License 2.0 with the Commons Clause).

The models tarjim downloads have their own licenses, and some of them forbid commercial use: check
the model licenses table above before using those models for work.

## Development

```bash
pip install -e ".[dub,dev]"
pytest && ruff check tarjim tests && mypy tarjim
```

Design decisions and measurements are recorded in [docs/decisions.md](docs/decisions.md).
See [CONTRIBUTING.md](CONTRIBUTING.md).
