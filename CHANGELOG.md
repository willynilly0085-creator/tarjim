# Changelog

## 1.0.53 (2026-10-29)

- **Cancelling a dub stops the paid voices at once.** ElevenLabs, Fish Audio and the other
  ready voices kept being asked for every remaining line after a cancel; now no new line is sent.

## 1.0.52 (2026-10-29)

A full review of tarjim, prompted by a clip whose last seconds had no subtitles.

- **Subtitles stay on time to the very end.** The cloud listener's times could drift up to
  11 seconds on longer clips, leaving the end without subtitles; they are now corrected from what
  the computer itself heard before timing.
- **Each speaker has a colour.** The main speaker stays white; the next ones are yellow, cyan
  and green. A reply said over someone else's sentence now shows at its own moment, and an
  exchange keeps its order even when the model swaps the lines.
- **Arabic lines with English words read in the right order**, long lines wrap instead of
  leaving the frame, and the outline is softer.
- **tarjim keeps running.** After sign-in it is started again whenever it stops, a second copy
  can no longer run beside it, a request made during an update or before a shutdown is not lost,
  and the browser extension starts tarjim by itself when it is off.
- **Translation is sturdier.** Subscription programs (Codex, Grok, Antigravity) can no longer
  hang a job; one failed batch is retried instead of discarding the work; a backup engine only
  fills what is missing; local engines get smaller batches and more time.
- **Video and sound.** Phone videos filmed upright, audio that starts late, 10-bit sources,
  non-standard audio, dubs shorter than the video, and long videos' voice separation are all
  handled; a cancelled or failed run no longer leaves a broken file or deletes a good one.
- **Page, extension and phone bot.** The bot checks a request before downloading and never
  blocks while fetching; the page says when tarjim is off; the extension finds TikTok and
  Facebook feed videos, explains refusals and asks before cancelling.
- Chinese, Japanese and Thai are timed by character, sounds-only and music-only clips no longer
  fail, and audio files can be dubbed.

## 1.0.51 (2026-10-28)

- **No code to connect the browser extension.** When the tarjim extension asks to connect, tarjim's
  page now shows only Allow and Deny: press Allow if you asked from tarjim's extension, Deny if
  not. The 4 digits are gone from the extension and the page, in the 14 languages.

## 1.0.50 (2026-10-28)

- **The extension's connection request says where its code is.** When the tarjim browser extension
  asks to connect, the page now says to click the extension's icon at the top of the browser,
  where its 4 digits show, to type them and press Allow, and to press Deny if you did not ask for
  it. Before, it only said "type the code", without saying where to find it. In the 14 languages.

## 1.0.49 (2026-10-27)

- **No console window after an update.** When tarjim restarted itself to use new code, Windows
  could open a terminal window titled `pythonw.exe` and leave it open while tarjim ran. The new
  engine now gets a console that is never shown. If a window like that is open now, you can close
  it once this version is in: tarjim starts again without it.

## 1.0.48 (2026-10-27)

- **Gemini works with a Vertex AI key.** A Vertex AI key (it starts with `AQ.`) reaches the same
  Gemini models billed to your Google Cloud project, without the free key's daily limit per model.
  Paste it in the Gemini key field on tarjim's page, or keep it in the `VERTEX_API_KEY`
  environment variable; tarjim finds a variable set in Windows' settings without a restart. When
  tarjim has both kinds, translation and listening use the Vertex key. Gemini voices for dubbing
  still need a Gemini API key from AI Studio, because Vertex AI does not offer them.

## 1.0.47 (2026-10-27)

- **A Gemini failure names every model and why.** When a free key had used up its day on the
  newer models (Gemini 3.8 Flash down to 3.5) and the last one left was busy, the error listed only
  that last model, four times, so it looked as if tarjim had chosen it over 3.8. Now it lists each
  model once with its reason ("daily quota used up" or Google's code), and the page says the free
  quota is used up, with what to do: add a paid key in Settings, come back tomorrow, or use local
  mode. Gemini 3.8 Flash stays the first model asked, and the model picked in Settings goes before
  it.

## 1.0.46 (2026-10-27)

- **Updates take effect again.** tarjim downloaded new versions but could keep running the old
  one: when it restarted to use the update, it found its own log file held shut by the program
  that had started it, gave up, and stayed on the old code, so the browser extension stayed old
  too. The restart now writes to a second log beside the first (`server-restart.log`) and goes
  ahead. If your tarjim is stuck on an older version, close it and open it once; after that,
  updates restart it by themselves. Then press Reload on tarjim in Chrome's extensions page.

## 1.0.45 (2026-10-27)

- **The translator next to Translate only offers what works.** A local AI program without a model,
  or a provider without its key, is no longer offered or saved, so a job no longer fails later at
  the translation step. When the saved translator stops working, the line above Translate says
  "not working now" and the list asks you to pick another. If the list cannot load, it says so and
  offers Try again, instead of "Couldn't save that".
- **Dubbing voices that need a key you have not added are marked** and cannot be picked, instead
  of being swapped quietly for the voice on your computer. A dub into a language the voices on your
  computer do not speak is refused when you press Translate, not at the end of the work.
- **Sending says what went wrong:** a file over 8 GB, tarjim not running, a bad link, or a voice
  that needs its key. A chosen file has a Remove button, typing a link sets the file aside, and a
  file dropped anywhere on the page is taken instead of being opened by the browser.
- **Recent translations stay after a restart of the computer.** Cancel asks once before deleting
  the work done so far. Play, Show in folder, Pause, Cancel and Try again say why when they could
  not act (a file that was moved, for example), and the list no longer waits for the voice
  services to answer.
- **Smaller fixes:** failure reasons keep their line breaks; a subtitle file's button reads "Open
  subtitles"; the page remembers your last language, output and voice; the page language menu is
  named in your language; and stage names no longer get cut on a phone.

## 1.0.44 (2026-10-27)

- **The extension says where AI keys go.** Under the translator in the popup, a line now says that
  Gemini and other AI keys are added on tarjim's page, with "Add a key" opening the page right on
  its key settings (`#connect`, the "API key" tab). Settings in the popup has the same button.
- **A failed press says why, on that video.** Play, Show in folder, Pause, Cancel, Try again and
  Remove used to show "tarjim is not running" for any failure, or nothing at all, and Remove said
  "removed" even when it was not. Each now says what happened under its own video.
- **A translation tarjim refuses says why**, for example a file over 8 GB (now caught before it
  uploads) or a link that is not a video link.
- **Key and quota messages no longer blame Gemini** when another provider is used; they say the
  same as tarjim's page in every language, and checking a Fish key no longer says "with Google".
  Saving the settings with no key typed no longer says it is checking one.
- **Voices that need a key you have not saved** are marked "needs a key" in the popup and cannot be
  picked, with a link to add the key; the right-click menu leaves them out until the key is saved.
  A Gemini key kept only in `GEMINI_API_KEY` counts here too.
- **"Connect automatically" keeps the popup open.** tarjim's page opens behind it, and the code also
  stays in a notification until the request is answered. An expired request or a tarjim that stops
  answering is now said as such, not as "denied".
- **Smaller fixes in the popup:** the settings summary says when it could not be read instead of
  "Loading…" forever; "Try again" and "I finished" say so when nothing changed; Arabic calls the
  program ترجم throughout; manual pairing with the security token sits under its own heading, and
  the `tarjim-serve` command is no longer shown on Windows.

## 1.0.43 (2026-10-27)

- **A Gemini key can be saved again.** Since an update of Google's library, checking a Gemini key
  failed every time, and the page said the provider refused it, even for a good paid key. The
  check works again, and it now says "refused" only when Google refuses the key; when Google could
  not be reached or a limit was hit, it says so instead.
- **The big Save button saves the key you typed.** A key pasted without pressing "Check and save"
  was dropped while the page said "saved". Now it is checked and saved first.
- **The key you save on tarjim's page is the one tarjim uses**, also when an older key sits in the
  `GEMINI_API_KEY` environment variable (left by Gemini CLI, for example). A key only in that
  variable now shows as set. If you had been relying on that variable, save the key on the page.
- **Clearer key screens.** The key field says how to replace a saved key, the model list says it
  appears after the key is saved, and the words under the listening choice match the one picked.
  "Use the AI you pay for" now offers "Use my key" right away, since a Gemini key is not a
  subscription, and the Gemini key option reads "API key, free or paid".

## 1.0.42 (2026-10-26)

- **Translating with Gemini takes seconds again, in every language.** A one-minute clip into Saudi
  Arabic could take 8 to 13 minutes. Gemini translates with the clip's sound beside the text, and
  with sound it kept its long default thinking, which sometimes ran to its ceiling (200 seconds
  for 17 lines, in Arabic or English alike), while tarjim waited up to 4 minutes for each model
  and asked the same stuck model again. Translation now thinks briefly (the same lines take about
  3 seconds), gives up on a model sooner for short clips, and a model that kept a job waiting is
  asked last for the next 20 minutes. Listening is unchanged.

## 1.0.41 (2026-10-26)

- **The chat connection keeps working when tarjim moves to a newer Python.** A copy run from
  source removed its old environment as soon as tarjim ran on the new one, while the chat
  connections Claude had started still ran from the old one, so their tools could no longer reach
  tarjim. The old environment now stays until nothing runs from it. If tarjim's tools in Claude
  answer with an error after the move to 1.0.40, restart the Claude app once.

## 1.0.40 (2026-10-26)

- **tarjim runs on Python 3.12, and its libraries take their newest versions:** numpy 2.5.4,
  scipy 1.18.1, librosa 1.0.0 and networkx 3.7, which needed Python 3.12. The update moves your
  copy by itself: an installed copy is set up again on Python 3.12, and a copy run from source
  gets a new environment on it, with the old one kept until tarjim runs on the new one. It
  downloads the libraries again (about 3 GB with PyTorch for a graphics card) the first time.
  Intel Macs stay on numpy 1.26 and PyTorch 2.2, the last versions made for them.

## 1.0.39 (2026-10-26)

- **Updates can move tarjim onto a newer Python.** A release now says which Python it runs on, and
  the update installs it there: the installed copy is set up on that Python, and a copy run from
  source gets a new environment on it, with the old one kept beside it until tarjim runs on the
  new one (and put back if the new one cannot be made). Nothing moves yet: this release still runs
  on Python 3.11. It prepares the next one, which moves to 3.12 so numpy, scipy, librosa and
  networkx can take their newest versions.

## 1.0.38 (2026-10-26)

- **A copy run from source updates itself.** It used to say "updated with git" and wait. Now it
  updates like an installed copy: with automatic updates on, while nothing runs (or with Update
  now), tarjim closes, moves the clone forward to the new release, installs the libraries tested
  with it, and starts again. A clone with commits of its own is never merged: it is left as it is
  and the page says the update failed. If the libraries cannot be installed, the code goes back
  to where it was.
- **Four libraries move to their newest versions:** importlib-metadata 10.1.0, multidict 7.2.1,
  starlette 1.10.0 and sse-starlette 3.6.0. The others with newer releases wait for a reason:
  numpy 2.5, scipy 1.18, librosa 1.0 and networkx 3.7 need Python 3.12 or later, and tarjim runs
  on 3.11; mpmath 1.4 and tenacity 9.2 are held by other libraries. None of the versions tarjim
  uses has a known vulnerability.

## 1.0.37 (2026-10-24)

- **The automatic checks on Linux pass again.** Since 1.0.35 the type check stopped at the Windows
  registry lookup for the desktop's folder, so the tests never ran on Linux. The lookup now runs
  on Windows only, and one test that read the names of programs tarjim had started no longer
  fails when one of them ends while it reads. Nothing changes in how tarjim works.

## 1.0.36 (2026-10-24)

- **You pick the quality a link downloads in.** tarjim used to download 1080p or less by itself.
  Now a link shows the qualities it really offers (2160p, 1440p, 1080p, 720p and so on), each with
  its approximate size, before anything downloads, and downloads exactly the one you pick with its
  sound. 1080p, or the nearest below it, is picked each time unless you pick another; "sound only"
  is offered when you want a subtitle file; a quality past the 8 GB limit cannot be picked. It
  works on tarjim's page, in the extension (the right-click menu now opens its window on the
  link, so you pick there), from chat (your AI shows the qualities and asks before it starts) and
  in the phone bot (buttons after the kind of result). A playlist link says so before you start.
- **Burned subtitles keep the video's quality.** Most videos from YouTube and other sites are AV1
  or VP9, which need about half as many bits as the H.264 tarjim writes, and the burned video was
  held to the source's own rate, so it came out softer. The limit now allows for the source's
  codec: on a 1080p AV1 clip the burned video went from 0.9936 to 0.9970 similarity to the
  source, at 5.0 MB instead of 3.1 for 20 seconds.

## 1.0.35 (2026-10-24)

- **The tarjim shortcut starts tarjim when it has stopped.** The shortcut on the desktop only
  opened tarjim's page, which could not load once the engine had stopped, and the extension then
  asked for a terminal command. Now the shortcut, on the desktop and in the Start menu, starts
  tarjim without a window when it is not running and then opens its page (about four seconds);
  when it is running, the page opens at once. The extension says to double-click it. The plain
  link an earlier version put on the desktop is replaced by itself the next time tarjim starts.

## 1.0.34 (2026-10-24)

- **tarjim starts with your computer more reliably, and says why when it cannot.** If the engine
  started at sign-in is gone a minute later, tarjim starts it once more. Every start and stop is
  now written with its time to `~/.tarjim/server.log`, including an error that used to vanish
  before the engine had opened its log, so a failed start explains itself.

## 1.0.33 (2026-10-23)

- **Local listening is more accurate, faster, and free of known vulnerabilities.** It now runs on
  Qwen's own Transformers models (Qwen3-ASR-1.7B-hf and its aligner) instead of the qwen-asr
  package, which held transformers on an old version with six known advisories. Measured on the
  same speech: Arabic word errors fell from 14.9% to 6.0%, English from 4.0% to 2.9%, 10–20%
  faster on a graphics card, and 2–3 GB of memory instead of 5 while it works. Your current
  models keep working; the new ones download in the background while tarjim is idle, and the old
  ones are removed once the new ones are verified. A full vulnerability check of every library
  now finds nothing.
- **Burned subtitles and the phone copy work on every computer.** tarjim's own ffmpeg has no x264,
  so without an NVIDIA card both failed. tarjim now tries Intel and AMD encoders, x264, then
  OpenH264 and Windows' own encoder.
- **Libraries at their newest tested versions:** transformers 5.20, huggingface-hub 2.3,
  certifi 2026.10.23 and the rest; qwen-asr, gradio and their dependencies are gone.

## 1.0.32 (2026-10-23)

- **tarjim keeps the programs it brings up to date by itself.** On Windows, for people who did
  not have them, tarjim installs its own Node.js (for Codex and Copilot) and its own ffmpeg; it
  installed them once and never again, so security releases never reached those people. Now,
  once a day while nothing is running, each is checked against its maker's latest release,
  verified against the published checksum (a mismatch is refused), put in place beside the old
  one, and the old one kept until the new one works. The Codex and Copilot installed with that
  Node.js move with it. A Node.js or ffmpeg you installed yourself is never touched.
- **Python 3.11 under tarjim stays current too.** When a newer 3.11 security release is out,
  tarjim's environment is rebuilt on it once, while nothing is running.
- **20 libraries moved to their newest tested versions**, among them google-genai 2.33,
  websockets 17 and python-dateutil 3, checked with real listening, burning, own-voice dubbing
  and a Gemini translation.
- **Saving settings no longer fails when the settings file is on another drive.**

## 1.0.31 (2026-10-22)

- **The phone bot asks Saudi or standard Arabic.** After you choose what to make of a link or a
  video, an Arabic translation asks one more question on the same message: Saudi or standard. The
  style you chose last is first and marked, one tap away. Other languages start right away.
- **25 known library vulnerabilities closed.** pillow 13.0.0 and certifi 2026.10.19, tested with
  this release (local listening gave the same words on a real clip).

## 1.0.30 (2026-10-19)

- **Subtitles move clear of text already in the video.** When a clip already has words burned
  in (the creator's own captions, a channel name, a news ticker), tarjim's subtitle used to land
  right on top of them. tarjim now looks at a few frames first and raises its subtitle above that
  text, or moves it to the top when there is no room; with nothing in the way it stays where it
  was. It takes under a second on most computers and never holds a translation up.
- **Videos carry tarjim's mark.** The logo with @Cut_Code, small and half-see-through: bottom
  left on wide videos, top left on tall ones (where TikTok and Reels put their own text at the
  bottom), always clear of the subtitles. Settings turns it off. Subtitle files carry no mark.
- **No black window when tarjim updates itself** on Windows.

## 1.0.29 (2026-10-17)

- **Right-click "translate" works while tarjim restarts.** tarjim restarts by itself for a few
  seconds after an update; a translation asked for in that moment, from the right-click menu,
  the extension's window or a job kept while pairing, now waits for it instead of saying tarjim
  is off.
- **A translation cancelled while it was still waiting shows as cancelled at once**, and can be
  removed from the list right away.

## 1.0.28 (2026-10-15)

- **Antigravity translates in seconds and no longer stops with "no output produced".** Its
  heavier models (Medium, High) took minutes for the same translation and sometimes reached for a
  terminal command, which Antigravity refuses without asking, and then answered nothing.
  Translation now uses the light variant of the model you chose and is told to answer directly
  without any tool. Measured on the same clip: High failed after 209 seconds before, 20 seconds
  now, with the same Saudi translation.

## 1.0.27 (2026-10-15)

- **Remove a translation from the list.** A finished, failed or cancelled translation has a
  "Remove from list" button, on the page and in the extension. The video and subtitle files stay
  in your folder; a finished one asks once before it goes.
- **Change the translating AI and its model without redoing setup.** A short line above
  Translate shows which AI and model translate ("Translating with Gemini · 3.8 Flash"). Change
  opens a list of the AIs that are ready now and that AI's text models; the choice is saved at
  once and the next translation uses it. On the page and in the extension.

## 1.0.26 (2026-10-15)

- **Translation by Gemini key takes seconds again, not minutes.** When Google's busiest models
  were under load, Google's own library retried them in silence for minutes; now a busy model
  gives way to the next one at once, and one that has not answered in 90 seconds is left for the
  rest of the job. The model you pick is now really used (before, a fixed list was), and Gemini 3
  translates with short thinking. Measured on the same clip: 3 to 4 minutes before, 14 seconds now.
- **The Gemini model list shows text models only.** Music, image, video, robotics and agent
  models are no longer offered for translation.
- **Grok no longer stops with "max turns reached".** It gets three turns instead of one.
- **Antigravity tries a translation again** when Google drops its answer halfway.
- **The setup plan opens quickly.** About 2.5 seconds the first time and at once after that
  (5 to 6 seconds every time before).
- **No more "cannot import name" after an update from source.** A running tarjim keeps the code
  it started with, and when its files change it restarts into the new code by itself once no job
  is running; your job list is kept.

## 1.0.25 (2026-10-15)

- **One library vulnerability closed, the rest disclosed and blocked.** accelerate now installs at
  1.15.0, past a known path-traversal issue (checked by listening to real Arabic and English
  speech: the same words and timings as before). Six known issues in transformers cannot be
  closed yet: the local listening library (qwen-asr) only works with the affected version. tarjim
  now blocks the ways they could be reached: every model downloads and loads from one fixed,
  checked version, as settings and safetensors files only, never code; the voice-separation and
  vowel-mark models are checked before use. Settings shows the issues that still apply to your
  copy, with the reason; the notice disappears by itself when an update brings the fix, which a
  weekly check watches for. Details in SECURITY.md.
- **Own-voice dubbing works on a new computer.** A fresh install lacked torchaudio, which the
  voice model needs.
- **tarjim installs on a Mac.** The vowel-mark model has no Mac build and stopped the whole
  install; on a Mac the voice now gets the text without vowel marks.

## 1.0.24 (2026-10-15)

- **yt-dlp, the downloader, keeps itself current.** Sites change every few weeks and an old
  downloader stops working. With automatic updates on, tarjim asks once a day for the latest
  yt-dlp and installs it while nothing is downloading; the next download uses it, with no
  restart. A failed try keeps the old one and is tried again the next day.
- **Every other library is installed at the versions tested with the release.** Each update
  rebuilt tarjim's environment with the newest version of every library that day, untested.
  Now the release carries the list of tested versions and the install follows it. An existing
  install is brought onto them once, by itself, a minute after this version starts (when no job
  is running). A weekly check on GitHub tries the newest versions against tarjim's tests and
  known vulnerabilities before they reach anyone.

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
