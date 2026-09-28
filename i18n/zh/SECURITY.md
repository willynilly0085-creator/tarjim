# 安全
<!-- languages -->
[English](../../SECURITY.md) · [العربية](../../i18n/ar/SECURITY.md) · [Español](../../i18n/es/SECURITY.md) · [Français](../../i18n/fr/SECURITY.md) · [Português](../../i18n/pt/SECURITY.md) · [Deutsch](../../i18n/de/SECURITY.md) · [Русский](../../i18n/ru/SECURITY.md) · [Türkçe](../../i18n/tr/SECURITY.md) · [हिन्दी](../../i18n/hi/SECURITY.md) · [اردو](../../i18n/ur/SECURITY.md) · [Bahasa Indonesia](../../i18n/id/SECURITY.md) · [日本語](../../i18n/ja/SECURITY.md) · **中文** · [한국어](../../i18n/ko/SECURITY.md)

## 报告问题

请通过本仓库上 GitHub 的 "Report a vulnerability"（报告漏洞）按钮私下报告安全问题，不要在公开的 issue 中报告。请描述你发现了什么、如何复现，以及它能让别人做什么。我们会尽快阅读并回复报告。

## tarjim 保护的内容

- **密钥和配对令牌** 通过 `keyring` 存放在操作系统的加密保管库中。它们绝不会出现在设置文件、服务器响应、日志或聊天工具中。
- **本地服务器**（`tarjim-serve`）仅监听 127.0.0.1，并拒绝：
  - 既没有令牌（`X-Tarjim-Token`）也没有页面的 HttpOnly、SameSite=Strict Cookie 的请求；
  - `Host` 不是本地地址的请求（DNS 重绑定）；
  - 并非来自浏览器扩展的配对请求；
  - 其自身网页文件夹和任务完成输出之外的任何路径。
- **订阅** 通过运行厂商自己的程序（Claude Code、Codex、Copilot、Antigravity）来使用。tarjim 绝不会读取或存储它们的登录文件或令牌。
- **本地模式** 让媒体始终留在设备上：模型在 Hugging Face hub 离线的状态下加载，只有在下载用户要求的工具时才会使用网络。
- **下载**：ffmpeg 会与随其发布版本公布的 SHA-256 进行校验。

## 已知限制

- 任何能在你的电脑上以你的用户身份运行程序的人，都可以读取保管库和令牌。tarjim 无法防御已被入侵的账户。
- 你选择的云服务商会按照其自身条款接收它们所处理的音频或文本。
