# Changelog

## 1.0.23 (2026-10-15)

- **Cancel stops a job at once, and the next one starts.** Cancel only took effect between steps,
  so a download handed to ffmpeg, a burn, or an AI program working on a translation kept running
  after the button was pressed, its partial file kept growing, and the next job waited. Now
  cancel stops every program the job started, the next job starts within about two seconds, and
  what the cancelled job left half-done is deleted (a fully received file stays for Retry).
  Two heavy local models are never loaded at once, even right after a cancel. Pause now also
  holds ffmpeg while it works on a file on this computer. Checked by hand on Windows.

## 1.0.22 (2026-10-15)

- **One size limit for the whole download.** A link's 8 GB limit now covers all of its pieces
  together (a video and its sound were each allowed 8 GB), and it also holds when the download is
  handed to ffmpeg, which before had no limit at all. Found by checking the previous release
  once more.

## 1.0.21 (2026-10-14)

- **Security hardening after a full scan.** A complete security scan of tarjim, run offline the way
  Anthropic's OSS Scanner works, found eight problems; all are fixed, each guarded by tests:
  pairing a browser extension now needs the code that extension shows, typed on tarjim's page;
  tarjim starts itself so a folder named `tarjim` in the open project can never stand in for it;
  Codex and Grok translate with every tool switched off; a file is opened by ffmpeg as itself
  only, so a playlist named like a video, a network-share path or a Windows device name is
  refused; a file's length is the sound it really holds, at most six hours, and cancel works
  while listening; a link to a list of videos is refused before anything is downloaded; and work
  for a file translated from a chat is kept under tarjim's own folder and cleared weekly.

## 1.0.20 (2026-10-13)

- **An account the AI company refuses is now named as that.** When a subscription answers that
  the account is not eligible or must be verified first (Google Antigravity does this for some
  accounts), tarjim said "an unexpected error". It now says the company refused the account,
  that this is not on tarjim's side, and what to do: finish the company's verification, or
  choose another AI. The company's own words still appear under it. On the page, in the
  extension and in the phone bot, in the 14 languages.

## 1.0.19 (2026-10-12)

- **A program you install after tarjim started is now found.** tarjim runs in the background and
  kept looking for Claude Code, Codex, Node.js and the others on the PATH it was started with, so
  a program installed afterwards was reported as missing until the computer restarted. It now
  also reads the computer's current PATH from Windows on every look, and npm's own folder.
- **A download that stops in setup now says why.** The screen showed only "stopped, check the
  internet"; it now shows the downloader's own error for each part (no connection, time-out,
  disk full). A dropped download is also tried again by itself up to four times before it is
  reported, and it continues where it stopped.
- **Downloads no longer fail with "Access is denied" on the model folder.** On a computer where
  the shared model folder (`.cache\huggingface` in the user folder) cannot be written, which is
  what stopped a new person's setup, tarjim now keeps its models in its own folder
  (`.tarjim\models`) and remembers it. Where the shared folder works nothing changes.
- Shown on this computer: started with a PATH that had none of them, the old lookup found
  nothing and the new one found Claude Code, Codex, Grok and npm. Not tested on another computer.

## 1.0.18 (2026-10-12)

- **Choose any subscription in setup, installed or not.** The setup plan now lists every
  subscription (Gemini through Antigravity, Claude, ChatGPT, Grok, Copilot). When the program of
  the one you choose is not on the computer, the same screen installs it and then signs you in;
  nothing is typed in a terminal. Before, a subscription whose program was missing was not
  offered at all, so a person with nothing installed saw only the key choices.
- ChatGPT and Copilot no longer send you to install Node.js: on Windows tarjim downloads the
  official portable Node.js (about 38 MB) into its own folder and installs the program beside
  it. Nothing else on the computer changes.
- A failed install now shows what the installer itself said, and can be tried again. An installer
  that ends without leaving its program behind counts as failed instead of waiting ten minutes.
- When both a program and a key are still needed, both are shown, not only the key.
- Tested on Windows 11 as a person with no AI program and no Node.js, from the setup screen:
  Gemini (Antigravity), Claude, Grok and ChatGPT were each installed and found. Sign-in was then
  offered for Claude and Grok; for Gemini and ChatGPT it could not be tested here, because the
  test shared this computer's saved sign-in. Copilot, Windows 10, macOS and Linux were not tested.

## 1.0.17 (2026-10-12)

- **Install with one file.** Download tarjim from GitHub, unzip it and double-click `install`:
  it installs everything, starts tarjim in the background with no window, makes it start with the
  computer, puts a shortcut on the desktop and opens the page where setup continues. Nothing has
  to be installed first, and no terminal is needed. Before, installing meant typing commands, and
  the engine ran in a console window that had to stay open.
- The README now says what the install downloads (about 4 GB), how much each part is and why it
  is there, and what the setup page downloads afterwards for each choice.
- Tested by running the file where the installer tool was missing: it installed it, installed
  tarjim and started the engine. Not tested on Windows 10 by us.

## 1.0.16 (2026-10-11)

- **A Gemini subscription can now listen.** If you are signed in to Google's Antigravity, pick
  "Gemini (Google Antigravity)" under listening: your plan hears the speech, with no API key and
  without downloading the listening model (about 6 GB) or needing a graphics card. The timing of
  every word is still worked out on your computer. The audio of each clip is sent to Google, as
  with a Gemini key. On a computer without a strong graphics card, setup now suggests it when you
  are signed in.
- Measured before release: six minutes of English and Arabic speech heard to the last second in
  48 seconds; a 94-second clip with seven speakers through tarjim's full listening path (three
  passes and the vote) in 16 to 95 seconds depending on how busy Google's service was.
- Claude, ChatGPT (Codex) and Grok subscriptions were tested with the same audio file and cannot
  take audio, so they stay translation only.
- When listening passes agree on the words but place them seconds apart, the vote no longer drops
  whole lines: the fullest pass is kept. This applies to every cloud listener.

## 1.0.15 (2026-10-10)

Security fixes from a full read of the code against tarjim's threat model. Update when you can.

- **A saved key no longer follows a changed address.** Changing the custom API address, or the
  address or service of a linked voice, now clears the key saved for the old one, so you type it
  again on tarjim's page. Before, an assistant steered by text it had read could point the
  address at another server and the next request would have carried your key there.
- **Pairing shows a number.** When a browser extension asks to connect, the extension and
  tarjim's page now show the same four-digit number; allow the request only when they match.
  Asking again replaces the earlier request instead of queueing behind it, so another extension
  can no longer leave a request waiting for your click.
- **No link can start a job.** The old `/translate?url=...` address is removed; work starts only
  from the page, the extension, a chat tool or the phone bot.
- **Files on this computer only.** A job from a file path refuses network shares, so opening a
  path can no longer make Windows sign in to someone else's server.
- **Local AI programs are looked for where programs are installed**, not through the whole home
  folder, so a file that merely has the right name in Downloads is never started.
- **Downloads have an end.** A link download stops at 8 GB, refuses live broadcasts, and Cancel
  now stops it while it is running.
- **Subtitle files carry text only.** Drawing and styling commands (`{\...}` and `<...>` tags)
  from a model's answer are removed from `.srt` files, as they already were from burned
  subtitles.
- Dubbing refuses soundtracks longer than six hours instead of running out of memory.
- File names from Telegram follow the same rules as uploads; only `http` and `https` links are
  taken from a message.
- Errors shown by the connection test and by tool downloads pass through the same masking as job
  errors.
- The extension no longer sends addresses inside your home network (private ranges, `.local`)
  to tarjim, including the post link it finds around a video.

Known and not fixed in this release: updates and tool downloads are fetched over HTTPS from
their publishers but not checked against a pinned hash; the Codex, Copilot and Antigravity
programs are run in an empty folder with their sandbox on, but their own tools are not yet
switched off the way Claude's and Grok's are.

## 1.0.14 (2026-10-09)

- The phone bot now shows a progress bar with the megabytes on every transfer, not only on large
  videos: a small video coming in, the result going back to your phone, and a link (YouTube, X
  and the rest) being downloaded on your computer, where the bar sits on its line of the
  checklist.
- To tell how far an upload is, the result is now sent as it is read from disk instead of being
  built whole in memory first, so a 50 MB result no longer takes 50 MB of memory to send.
- A job's state now carries how many bytes of its download have arrived, for anything that
  shows jobs.

## 1.0.13 (2026-10-09)

- **Large videos through the phone bot, up to 2 GB.** Telegram lets a bot take only 20 MB and
  return 50 MB. With an app id and hash that you create once for free at my.telegram.org and save
  in tarjim's phone settings, the bot takes videos up to 2 GB and returns the result whole, with
  no smaller phone copy. Tried on a real 48 MB video: taken, subtitled and returned.
- While a large video downloads or uploads, the bot's message shows a bar and the megabytes so far.
- A video over 20 MB with large videos off is answered with how to turn them on, not "send a
  link instead".
- **A burned video is no longer two to three times the size of its source.** The result may now
  spend 15% more than the source did and no more. Measured on the same clip: 127 MB before,
  52 MB now, from a 48 MB source, and the two results look the same (SSIM 0.989).
- The app hash and the bot's sign-in are kept in the system vault like the keys; no chat tool
  can read or set them.

## 1.0.12 (2026-10-09)

- An assistant in chat (Claude, Claude Code, Codex) can now change every setting the page can:
  scan the computer and apply the suggested setup, install a subscription's program, start or find
  the AI programs on the computer, choose the dubbing voice service, set the phone bot's language
  and result, turn starting with the computer and automatic updates on or off, check that the
  setup works, and update tarjim. Before, it could change the engines, the tools and the glossary
  only.
- Keys and bot tokens are still never taken in chat: no tool accepts one, a test keeps it that
  way, and the assistant opens tarjim's page for you to type them. Allowing a browser extension
  to pair also stays with you.
- A computer whose graphics card has less than 8 GB is no longer advised to listen on the
  computer (the listening model needs about that much); Gemini is suggested and the reason is
  shown. Before, any graphics card was enough for that advice.

## 1.0.11 (2026-10-09)

- The voice services you can link for dubbing are now listed by name, each with a link to get its
  key: **Google Gemini**, **ElevenLabs**, **Fish Audio**, **OpenAI**, **Groq**, **OpenRouter** and
  **Together AI**, plus "another voice service" for any address in OpenAI's speech format. In
  1.0.10 the list had only ElevenLabs and the open address.
- A named service brings its own model and voices for the language you dub into, so there is
  nothing to type but the key. Groq brings its Saudi Arabic voices (Abdullah, Noura, Fahad, Lulwa,
  Sultan, Aisha) and its English ones; a long line is sent in parts because Groq takes 200
  characters at a time.
- A service that has no voice for the language says so instead of speaking it badly (Groq speaks
  Arabic and English, Together AI's listed model English).
- Not tested with real keys: each named service's address was checked only as far as it refusing
  a made-up key. Not added because their own documentation could not be confirmed: xAI's Grok
  voices, Mistral's Voxtral, MiniMax and Deepgram; Voxtral and others can be reached through
  OpenRouter by typing the model name.

## 1.0.10 (2026-10-09)

- Dubbing is no longer limited to the voices tarjim came with. Link a voice service with your own
  key: **ElevenLabs** (ready voices from your library, a different one per speaker, or each
  speaker's own voice cloned for the job and deleted from ElevenLabs when it ends), or **any
  service that speaks OpenAI's speech format** (you give its address, key, model and voice names).
- A new "Dubbing voice" step in setup and Settings, and a line in the setup plan. The linked
  voices appear in the voice list of the page and the extension, and as buttons in the phone bot,
  once the key is saved.
- A linked voice is used as it is or not at all: without its key the job says so, and it is never
  swapped for another service.
- Not tested with a real key: ElevenLabs and the open speech format were built from their API
  references and checked against ElevenLabs only as far as a refused key goes. If you use one,
  please report what you see.
- Gemini's subscription (through Antigravity) translates but cannot dub: that program answers in
  text only, so Gemini's natural voices still need a Gemini API key.

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
