# 贡献指南
<!-- languages -->
[English](../../CONTRIBUTING.md) · [العربية](../../i18n/ar/CONTRIBUTING.md) · [Español](../../i18n/es/CONTRIBUTING.md) · [Français](../../i18n/fr/CONTRIBUTING.md) · [Português](../../i18n/pt/CONTRIBUTING.md) · [Deutsch](../../i18n/de/CONTRIBUTING.md) · [Русский](../../i18n/ru/CONTRIBUTING.md) · [Türkçe](../../i18n/tr/CONTRIBUTING.md) · [हिन्दी](../../i18n/hi/CONTRIBUTING.md) · [اردو](../../i18n/ur/CONTRIBUTING.md) · [Bahasa Indonesia](../../i18n/id/CONTRIBUTING.md) · [日本語](../../i18n/ja/CONTRIBUTING.md) · **中文** · [한국어](../../i18n/ko/CONTRIBUTING.md)

感谢你的帮助。以下几条规则能让 tarjim 保持易读，并且可以放心地修改。

## 提交拉取请求之前

```bash
pip install -e ".[dub,dev]"
pytest
ruff check tarjim tests
mypy tarjim
```

以上四项必须全部通过。这些限制由 `pyproject.toml` 中的配置强制执行：文件少于 200 行，函数少于 20 条语句且复杂度不超过 6，参数最多 4 个，每行少于 100 个字符，并通过 `mypy --strict`。

## 本项目的修改方式

- 先编写会失败的测试，再编写让它通过的代码。
- 先测量，再下结论：涉及计时、质量和速度的修改须附上证明它们的数据，并以带日期的一行记录在 `docs/decisions.md` 中（只追加）。
- 用名称表达含义；注释只解释代码本身无法说明的内容。
- 界面文字放在语言文件中（`tarjim/web/i18n`、`tarjim/extension/_locales`），使用简明的沙特阿拉伯语和英语。界面中不使用表情符号。
- 任何功能都不得把用户的媒体或密钥发送到用户未选择的地方。本地模式必须保持零外部连接。
