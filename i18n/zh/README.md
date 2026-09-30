# tarjim
<!-- languages -->
[English](../../README.md) · [العربية](../../i18n/ar/README.md) · [Español](../../i18n/es/README.md) · [Français](../../i18n/fr/README.md) · [Português](../../i18n/pt/README.md) · [Deutsch](../../i18n/de/README.md) · [Русский](../../i18n/ru/README.md) · [Türkçe](../../i18n/tr/README.md) · [हिन्दी](../../i18n/hi/README.md) · [اردو](../../i18n/ur/README.md) · [Bahasa Indonesia](../../i18n/id/README.md) · [日本語](../../i18n/ja/README.md) · **中文** · [한국어](../../i18n/ko/README.md)

**为任何视频生成字幕和配音，用你的语言，在你自己的电脑上完成。**

粘贴一个链接或拖入一个文件即可。tarjim 会聆听音频，把每一行精确对齐到说出它的那一刻，区分每位说话人，翻译成自然的口语，然后把字幕烧录进视频、生成 `.srt` 文件，或者为每位说话人配上各自的声音进行配音。

## 功能

- **任意来源：** YouTube、X 及其他链接（yt-dlp），或你设备上的任意视频或音频文件。
- **34 种目标语言**，涵盖从右到左和从左到右的书写方向。阿拉伯语默认使用沙特方言，一键即可切换为现代标准阿拉伯语。
- **仔细聆听：** 音频会被识别三次，每个词都经过投票决定，因此单次听错不会出现在字幕中。
- **精确计时：** 在你的电脑上把词语与音频对齐（CTC 强制对齐加语音活动检测）。字幕绝不会跨越镜头切换，延续到下一个人的镜头里。
- **识别说话人：** 对话行以破折号标出，每位说话人一行。
- **配音：** 可为每位说话人选用自然的 Gemini 声音（按音高匹配）、在本地克隆每位说话人的声音（XTTS-v2）、录音室声音，或 Fish Audio。单独的配音脚本会按实际读音书写人名、把数字写成文字，确保声音读得准确。
- **三种使用方式：** 浏览器右键菜单（"ترجم للعربية"）、本地网页，或聊天：把 tarjim 添加到 Claude 应用、Claude Code 或 Codex 中，然后让它翻译一个链接。

## 连接 AI：三种方式

| 方式 | 可选项 | 说明 |
|---|---|---|
| API 密钥 | Gemini、OpenAI、Anthropic、OpenRouter、DeepSeek、Qwen、Mistral、Groq、xAI，或任何兼容 OpenAI 的地址 | Gemini 和 OpenAI 还可以用于聆听（语音转文字）。 |
| 你的订阅 | Claude（通过 Claude Code）、ChatGPT（通过 Codex）、GitHub Copilot、Google AI（通过 Antigravity） | tarjim 使用你的登录信息运行厂商自己的程序。用量计入你的套餐，并适用各厂商的条款。 |
| 在你的电脑上 | Ollama、LM Studio、Jan、llama.cpp、vLLM、KoboldCpp | 连同其模型一起自动发现。任何数据都不会离开你的设备。 |

你可以选择服务商提供的任意模型。如果所选引擎出错或配额用尽，而本地引擎可用，tarjim 会自动回退到本地引擎。

## 让 AI 帮你安装（一步完成）

在 Claude Code 中：

```bash
claude plugin marketplace add willynilly0085-creator/tarjim
claude plugin install tarjim@tarjim
```

然后告诉你的 AI"安装 tarjim"。它会在后台安装引擎（如果你有 NVIDIA 显卡，则安装显卡版本），在不打开任何窗口的情况下启动它，并打开设置页面。从此以后，你的 AI 会直接使用 tarjim 的工具，例如："把这个链接翻译成法语并烧录字幕"、"翻译时使用我的 Claude 订阅"、"切换到本地模型"。tarjim 是由你的 AI 操作的工具，而不是另一个需要你与之对话的助手。该插件需要 [uv](https://docs.astral.sh/uv/)。

其他 MCP 应用（Codex、Cursor 等）：安装引擎后，把命令 `tarjim-mcp` 添加为 MCP 服务器，例如 `codex mcp add tarjim -- tarjim-mcp`。Codex 会要求你批准每一次工具调用；如果想让 tarjim 的工具无需询问即可运行，请在 `~/.codex/config.toml` 的 `[mcp_servers.tarjim]` 下添加 `default_tools_approval_mode = "approve"`。

已测试：装有该插件的 Claude Code 会话读取了设置、设定了术语表、把一个 YouTube 链接翻译成西班牙语并返回了字幕；Codex（ChatGPT 套餐）读取了设置并设定了术语表。ChatGPT 网站和桌面应用目前还无法访问你电脑上的工具（它们只接受远程 MCP 服务器），因此如需使用 ChatGPT，请通过 Codex。

## 手动安装（Windows）

需要 Python 3.11，以及约 10 GB 磁盘空间用于存放本地模型。

```powershell
git clone https://github.com/willynilly0085-creator/tarjim
cd tarjim
python -m venv .venv
# NVIDIA graphics card: install the CUDA build of PyTorch first (the default one is CPU only)
.venv\Scripts\python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python -m pip install -e ".[dub]"
.venv\Scripts\tarjim-serve
```

打开 <http://127.0.0.1:17653>。设置页面会检查你的设备、连接 AI，并下载所需的一切，包括 ffmpeg（在 Windows 上会下载 ffmpeg，并与其公布的 SHA-256 进行校验）。即使没有可用的显卡，所有功能也都能在处理器上运行，只是速度较慢。

**macOS 和 Linux** 的步骤相同，改用 `.venv/bin/...`，另外执行 `brew install ffmpeg` 或 `sudo apt install ffmpeg`。这些平台尚未经过测试。

### 浏览器扩展

tarjim 就在你的浏览器里：右键点击任意视频或链接，选择 **ترجم للعربية**（或你的语言），然后选择字幕、烧录字幕或配音。弹出窗口会显示每个任务所处的阶段，并可以暂停、取消或打开结果。

在 Chrome 中打开 `chrome://extensions`，开启 **Developer mode**（开发者模式），选择 **Load unpacked**（加载已解压的扩展程序），然后选中 `~/.tarjim/extension` 文件夹。扩展会自动完成配对：在 tarjim 页面上点击 **Allow**（允许）即可。

### 聊天

在设置页面的"通过聊天使用 tarjim"步骤中，点击 Claude 应用、Claude Code 或 Codex 旁边的 **Add**（添加）。之后你的 AI 就能替你操作整个工具：

- "把这个链接翻译成阿拉伯语并配音"、"现在进行到哪个阶段了？"、"暂停"、"打开结果"；
- 更改设置："翻译时使用我的 Claude 订阅"、"切换到本地模型"、"列出我可以连接的 AI"、"把界面改成英文"；
- 把完成的字幕读给你听、重试失败的任务，或下载缺失的工具。

密钥绝不会通过聊天输入；这种情况下 AI 会为你打开 tarjim 页面。

### 命令行

```bash
tarjim video.mp4                 # Arabic (Saudi), burned into the video
tarjim video.mp4 --to fr         # any target language
tarjim video.mp4 --no-burn       # .srt and .ass only
```

## 隐私与安全

- **密钥** 存储在操作系统的加密保管库中（Windows Credential Manager、macOS Keychain、Secret Service）。设置文件中不保存任何密钥。
- **哪些数据会离开你的设备** 取决于你的连接方式：片段的音频会发送给你选择的聆听服务商，文本会发送给你选择的翻译和语音服务商。在本地模式下，任何数据都不会离开：这一点是在一次完整的本地任务（包括配音）中监控所有连接后测得的（外部连接为零）。模型以离线方式加载；只有在下载工具时才会使用互联网。
- **本地服务器** 仅监听 127.0.0.1。每个请求都需要令牌或页面的同站（same-site）Cookie，外部的 `Host` 请求头会被拒绝（防御 DNS 重绑定），网站无法访问它或请求配对，而且它不会提供自身文件夹之外的任何文件。

如需报告问题，请参阅 [SECURITY.md](SECURITY.md)。

## 模型许可证

tarjim 的代码不包含模型权重；模型需从其所有者处下载。其中一些 **不允许用于商业用途**：

| 工具 | 许可证 | 商业用途 |
|---|---|---|
| 计时对齐器 `MahmoudAshraf/mms-300m-1130-forced-aligner`（必需） | CC-BY-NC-4.0 | 否 |
| 声音克隆 XTTS-v2（可选，会征求同意） | Coqui Public Model License | 否 |
| 本地翻译 `aya-expanse:8b`（可选） | CC-BY-NC-4.0 | 否 |
| 本地聆听 Qwen3-ASR-1.7B 和 Qwen3-ForcedAligner | Apache-2.0 | 是 |
| ffmpeg（LGPL 构建） | LGPL-2.1 | 是 |

设置页面会在每个下载项旁边显示其许可证。

## 状态

已在配备 RTX 5080 的 Windows 11 上，以及在不支持显卡的全新安装环境中测试，范围包括：链接和文件、烧录字幕和 `.srt`、法语和阿拉伯语、暂停、继续、取消和重试、三种连接方式（Claude 和 ChatGPT 订阅、本地 Ollama）、聊天工具，以及上述安全检查。尚未测试：macOS、Linux、GitHub Copilot 和 Antigravity 订阅。

## 许可证

tarjim 对所有人免费，企业也不例外：你可以出于任何目的使用、研究、修改和分享它。唯一不允许的是**出售它**：任何人都不得出售 tarjim，也不得出售价值来自 tarjim 的产品或服务（包括托管和付费支持）。请参阅 [LICENSE.md](LICENSE.md)（Apache License 2.0 附加 Commons Clause 的摘要）；具有法律约束力的完整文本（英文）见 [../../LICENSE](../../LICENSE)。

tarjim 下载的模型各有其自身的许可证，其中一些禁止商业用途：在工作中使用这些模型之前，请先查看上面的模型许可证表格。

## 开发

```bash
pip install -e ".[dub,dev]"
pytest && ruff check tarjim tests && mypy tarjim
```

设计决策和测量结果记录在 [docs/decisions.md](../../docs/decisions.md) 中。
另请参阅 [CONTRIBUTING.md](CONTRIBUTING.md)。
