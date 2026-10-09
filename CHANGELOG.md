# Changelog

## 1.0.9 (2026-10-09)

- Gemini through Antigravity is now verified with a signed-in Google account: the page lists the
  account's own models by name (Gemini 3.8 Flash, Gemini 3.1 Pro and the rest), and a translation
  comes back through the subscription with no API key. In 1.0.8 the model list came out empty.
- The lightest Gemini model is suggested (about 10 s for six lines; the "high" one took 43 s for
  two), and the slow plan mode is no longer used.

## 1.0.8 (2026-10-09)

- A Google account's Gemini (Google AI Pro, Ultra, or the free allowance) is offered through
  Google's Antigravity CLI: tarjim installs it from the page, asks `agy models` for the models
  your account has, and runs it in plan mode with a sandbox. Google stopped serving personal
  accounts through Gemini CLI on 2026-06-18, so that program is not offered. Not verified yet with
  a signed-in account: the model list and a full translation.
- Any API key works without picking a model first: the model the provider's own list suggests is
  used and remembered.
- An API that refuses a temperature or a reply format (some reasoning models, some local servers)
  is asked again without them, and a reply that wraps its JSON in a sentence is still read.
- Claude: Haiku 5.5 is listed with the newest models, and the API default is Sonnet 5.5.
- An Anthropic API reply with no answer is a failure, not an empty translation.

## 1.0.7 (2026-10-09)

- A voice on your computer is never replaced by a cloud voice. Before, dubbing "in the speaker's
  own voice" into a language that voice does not speak (Urdu, Persian) sent the text to
  Microsoft's voices without saying so; now dubbing stops and says the language has no voice.
- When a natural (Gemini) voice fails and no voice is installed on the computer, you see why the
  natural voice failed, not a missing-module error.
- A Fish Audio dub where every line failed is a failure, not a video with background only, and a
  temporary voice uploaded to Fish is always deleted.
- A rejected Gemini key stops at once and is named as a key problem (before: 18 attempts and
  "all models failed"). An empty answer from listening is a failure instead of being kept.
- A video with no sound says so. An audio file with cover art is no longer treated as a video.
- Work kept beside a video is not reused for a different file with the same name.
- Pause and cancel take effect between dubbing steps; ffmpeg can no longer hang a job forever.
- A second dubbing job no longer holds two large models on the graphics card at once.
- The extracted audio (about 115 MB per hour) is deleted once the transcript is saved.
- Grok Build can be installed from the page (the button was never offered).
- README and SECURITY say plainly where keys are kept without a system vault, what is downloaded
  on the first dub, and what the local page does not protect against.

## 1.0.6 (2026-10-09)

- The page's cookie no longer carries the engine's token. It carries a value made from it that
  works only for requests the browser marks as coming from tarjim's own page, so a page served
  from another local port can no longer start jobs, and another program that reads the cookie
  cannot use it as the token.
- A program on a network share, or given without its full path, is never accepted as a local AI
  program to start.
- A failed job shows only the masked reason: anything that looks like a key, and the home folder,
  no longer reach the extension, the chat tools or the job list.
- Settings are not lost when the settings file is busy or damaged: a busy file stops the save, and
  a damaged one is kept as `config.broken.json`.
- A cut-off upload is refused instead of being queued as a half video.
- Copies of videos that tarjim keeps to work on (uploads and downloads from links, up to 8 GB
  each) are cleared a week after their last use. Results in your downloads folder are not touched.
- Two tool downloads at once no longer leave the engine online for model lookups afterwards.
- Linux: the Claude desktop settings are found in `~/.config`, and starting with the computer
  works when the Python path has spaces.

## 1.0.5 (2026-10-09)

- A video whose title has an apostrophe ("Don't", "I'm") is burned. Before, ffmpeg could not
  open the subtitle file and the job failed.
- A hyphen inside a word stays in dialogue lines ("Est-ce que", "twenty-one"). Before, the first
  hyphen of each speaker's part was removed.
- A translation that comes back empty is a failure, and the next engine is tried. Before, the job
  ended as done with empty subtitles. A single line left empty is listed by the quality check.
- When the chosen engine fails, its own reason is shown (for example "sign in again"), not the
  backup engine's. A reply that is not valid JSON moves on to the next engine.
- A number at the start of speech ("3 things") no longer gets a subtitle at 0:00.
- A missing optional second listener no longer stops a job after listening is done.
- Phone bot: it keeps answering after an unexpected error (a pairing code in non-English letters
  from a stranger used to stop it until the engine restarted), a started job is followed even when
  its first message cannot be shown, and a result that cannot be prepared is reported.

## 1.0.4 (2026-10-09)

- A video sent to the Telegram bot is taken even when Telegram's file server stalls partway: the
  download continues from where it stopped. Before, the bot waited five minutes, started nothing
  and said nothing. The message now shows "Downloading" on the tap, and a download that cannot
  finish is reported with what to do next.

## 1.0.3 (2026-10-08)

- A Grok subscription (SuperGrok, X Premium+) translates through xAI's own program, Grok Build:
  found on the computer, signed in through the browser, with the account's real model list.

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
