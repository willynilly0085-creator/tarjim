---
name: tarjim
description: Use when the person wants a video or audio translated, subtitled or dubbed (a link or a file on their computer), in any language, or wants to change tarjim's settings (how subtitles look, read and are timed, which AI listens or translates, their subscription, a local model, a glossary of names). Drives the tarjim tools; tarjim does the work on their computer.
---

# Using tarjim

tarjim is a tool on the person's computer. You operate it through the `tarjim` MCP tools; you do
not translate the video yourself.

0. If the `tarjim` tools are not there at all, their server did not start, and the usual reason is
   that [uv](https://docs.astral.sh/uv/) is not installed. Tell the person, and with their
   agreement install it (Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`;
   macOS and Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`), then ask them to restart
   this app so the tools load. On Windows they can instead download tarjim's ZIP from GitHub and
   double-click `install.cmd`, which needs nothing first.
1. Call `setup_status` first.
   - `missing`: call `install_tarjim`, tell the person it takes a few minutes, check
     `setup_status` again later, then `open_tarjim_page` so they can finish setup in the browser.
   - `installed but stopped`: call `start_tarjim`.
2. Translate with `translate_video(source, language, output, quality)`:
   - `source` is a link or a full local file path; `language` is a code such as `ar`, `en`, `fr`,
     `ja` (`ar-msa` for Modern Standard Arabic); `output` is `burned`, `subtitles` or `dubbed`
     (a voice after a dash, such as `dubbed-clone`).
   - A link is not started until the person picks its quality. Call it first without `quality`:
     the answer lists the qualities with their sizes and the default (1080p or the nearest
     below). Show them, ask which one, then call again with `quality` set to their pick
     (`1080`, `720`, `audio` for subtitles only, or `default`).
   - Follow with `translation_status` until it is `done`; then `open_result` or `read_subtitles`.
   - A finished job carries `post`: a summary ready to post (`short` fits a tweet, `long` is a
     fuller post). Offer it when the person wants to share the video; `write_post_summaries("no")`
     turns it off.
3. Settings: `get_settings`, `list_connections`, `use_connection(provider, model)`,
   `change_settings`, `set_glossary("name = translation")`, `list_tools` / `install_tool`.
4. The person's own taste (how subtitles look, read and are timed, listening, translation
   style, files, dub): `get_preferences(group, language)` returns every setting with its range,
   `change_preferences({key: value}, language)` saves (a refused value comes back with its
   Arabic reason, show it as is), `reset_preferences("all" | group | key)`, and
   `use_preset(name)`. For one video only, pass `output` to `translate_video` as
   `{"result": "burned", "tweaks": {key: value}}`.
5. Never ask for or accept API keys in chat. Keys are entered on the tarjim page
   (`open_tarjim_page`); subscriptions sign in with `sign_in(provider)`.
