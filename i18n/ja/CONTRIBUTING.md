# コントリビューション
<!-- languages -->
[English](../../CONTRIBUTING.md) · [العربية](../../i18n/ar/CONTRIBUTING.md) · [Español](../../i18n/es/CONTRIBUTING.md) · [Français](../../i18n/fr/CONTRIBUTING.md) · [Português](../../i18n/pt/CONTRIBUTING.md) · [Deutsch](../../i18n/de/CONTRIBUTING.md) · [Русский](../../i18n/ru/CONTRIBUTING.md) · [Türkçe](../../i18n/tr/CONTRIBUTING.md) · [हिन्दी](../../i18n/hi/CONTRIBUTING.md) · [اردو](../../i18n/ur/CONTRIBUTING.md) · [Bahasa Indonesia](../../i18n/id/CONTRIBUTING.md) · **日本語** · [中文](../../i18n/zh/CONTRIBUTING.md) · [한국어](../../i18n/ko/CONTRIBUTING.md)

ご協力ありがとうございます。tarjim を読みやすく、安全に変更できる状態に保つため、いくつかのルールがあります。

## プルリクエストを作成する前に

```bash
pip install -e ".[dub,dev]"
pytest
ruff check tarjim tests
mypy tarjim
```

4 つすべてが通る必要があります。制限は `pyproject.toml` の設定で強制されています。ファイルは 200 行未満、関数は 20 ステートメント未満かつ複雑度 6 以下、引数は最大 4 個、1 行は 100 文字未満、そして `mypy --strict` です。

## このプロジェクトでの変更の進め方

- まず失敗するテストを書き、次にそれを通すコードを書きます。
- 主張する前に計測します。タイミング、品質、速度に関する変更には、それを示す数値を添え、`docs/decisions.md` に日付付きの 1 行として記録します（追記のみ）。
- 意味は名前で伝えます。コメントはコードで表現できないことだけを説明します。
- インターフェースの文言は言語ファイル（`tarjim/web/i18n`、`tarjim/extension/_locales`）に置き、平易なサウジ方言のアラビア語と英語で書きます。インターフェースに絵文字は使いません。
- 本人が選んでいない送信先に、その人のメディアやキーを送ってはなりません。ローカルモードは外部接続ゼロを維持する必要があります。
