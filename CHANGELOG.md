# Changelog

## 1.0.2 (2026-10-08)

- A subscription that is installed but signed out can be chosen in the setup plan, and signing in
  happens right there. Before, the choice was greyed out with "sign in first" and nowhere to do it.

## 1.0.1 (2026-10-08)

- Every failure now says where it stopped, what it means and the real reason, in the page, the
  extension and the phone bot, with anything that looks like a key masked. Before, an error tarjim
  did not recognise showed only "Something unexpected went wrong".
- A subscription whose sign-in expired is named as that, with what to do, instead of an unknown
  error.
- The licence names the developer, Indicators (indicators.sa), as the rights holder.

## 1.0.0 (2026-10-08)

The first public release.

### Translate and dub

- Subtitles for any video, from a link or a file, from any language to any language: burned into
  the video or saved as a subtitle file, timed to the speech and aware of who is speaking.
- Dubbing with natural voices (Gemini), studio voices, Fish Audio, or each speaker's own voice on
  your computer (VoxCPM2, chosen in a blind listening test for natural Arabic).
- A glossary for names and terms, and Saudi or standard Arabic style.

### Connect any AI

- A key (Gemini, OpenAI, Anthropic, DeepSeek, OpenRouter, Qwen, Mistral, Groq, xAI, Kimi, GLM,
  MiniMax, OpenCode Zen, or any compatible address), a subscription you already pay for (Claude,
  ChatGPT, GitHub Copilot, Antigravity, OpenCode Go) signed in through the browser, or a model on
  your own computer (Ollama, LM Studio and others, found and started for you).
- Real model names from each provider, with a suggested model for translation.

### Where you use it

- A setup assistant that checks the computer, proposes a plan with a reason for every line and
  downloads only what is needed.
- A browser extension: right-click any video or link. It pairs itself, shows each job's stage and
  keeps your last choice one click away.
- Your phone, iPhone or Android, at home or away, through your own Telegram bot: send a link,
  choose the result, follow every step in one message and get the video back.
- Your AI assistant, through the plugin and MCP tools.
- The interface, the extension and the documentation in 14 languages.

### Stays up to date

- tarjim asks once a day for the latest release number and, when you allow it, updates itself
  while no job is running; the extension reloads itself to match.

### Private by default

- Keys live in the operating system's vault, the engine answers this computer only, the phone bot
  answers one paired account and opens no port, and addresses inside the home network are refused.
