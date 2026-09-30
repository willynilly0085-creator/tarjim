# tarjim
<!-- languages -->
[English](../../README.md) · [العربية](../../i18n/ar/README.md) · [Español](../../i18n/es/README.md) · [Français](../../i18n/fr/README.md) · [Português](../../i18n/pt/README.md) · [Deutsch](../../i18n/de/README.md) · [Русский](../../i18n/ru/README.md) · [Türkçe](../../i18n/tr/README.md) · [हिन्दी](../../i18n/hi/README.md) · [اردو](../../i18n/ur/README.md) · [Bahasa Indonesia](../../i18n/id/README.md) · **日本語** · [中文](../../i18n/zh/README.md) · [한국어](../../i18n/ko/README.md)

**あらゆる動画に、あなたの言語で字幕と吹き替えを。すべてあなたのコンピューター上で。**

リンクを貼り付けるか、ファイルをドロップするだけ。tarjim は音声を聞き取り、各行を発話の瞬間に合わせてタイミング調整し、話者ごとに区別し、自然な話し言葉に翻訳します。そのうえで字幕を動画に焼き込むか、`.srt` を書き出すか、話者ごとに声を割り当てて吹き替えます。

## できること

- **あらゆるソースに対応:** YouTube、X などのリンク（yt-dlp）、またはデバイス上の任意の動画・音声ファイル。
- **34 の翻訳先言語**（右から左、左から右の両方）。アラビア語はサウジ方言が既定で、正則アラビア語（フスハー）にもワンクリックで切り替えられます。
- **丁寧な聞き取り:** 音声を 3 回聞き取り、すべての単語を多数決で決めるため、一度の聞き間違いが字幕に残ることはありません。
- **正確なタイミング:** 単語はあなたのコンピューター上で音声に整列されます（CTC 強制アライメントと音声区間検出）。字幕がショットの切り替わりをまたいで次の人物のショットにはみ出すことはありません。
- **話者を認識:** 会話はダッシュ付きの行で表示し、1 人につき 1 行です。
- **吹き替え:** 話者ごとの自然な Gemini の音声（声の高さで割り当て）、各話者のローカル音声クローン（VoxCPM2）、スタジオ音声、または Fish Audio から選べます。専用の読み上げ用スクリプトが人名を発音どおりに、数字を言葉で書くため、音声が正しく読み上げます。
- **3 つの使い方:** ブラウザーの右クリックメニュー（「ترجم للعربية」）、ローカルの Web ページ、またはチャット。Claude アプリ、Claude Code、Codex に tarjim を追加し、リンクの翻訳を頼むだけです。

## AI との接続: 3 つの方法

| 方法 | 選択肢 | 補足 |
|---|---|---|
| API キー | Gemini、OpenAI、Anthropic、OpenRouter、DeepSeek、Qwen、Mistral、Groq、xAI、または任意の OpenAI 互換アドレス | Gemini と OpenAI は聞き取り（音声からテキスト）にも使えます。 |
| お使いのサブスクリプション | Claude（Claude Code 経由）、ChatGPT（Codex 経由）、GitHub Copilot、Google AI（Antigravity 経由） | tarjim は各ベンダー純正のプログラムを、あなたのサインイン情報で実行します。使用量はあなたのプランに計上され、各ベンダーの規約が適用されます。 |
| あなたのコンピューター上 | Ollama、LM Studio、Jan、llama.cpp、vLLM、KoboldCpp | モデルとともに自動で検出されます。データはデバイスの外に一切出ません。 |

各プロバイダーが提供する任意のモデルを選べます。選んだエンジンが失敗したり利用枠を使い切ったりした場合、ローカルエンジンがあれば tarjim は自動でそちらに切り替えます。

## AI でインストール（1 ステップ）

Claude Code で:

```bash
claude plugin marketplace add willynilly0085-creator/tarjim
claude plugin install tarjim@tarjim
```

あとは AI に「tarjim をセットアップして」と伝えるだけです。AI はバックグラウンドでエンジンをインストールし（NVIDIA のグラフィックカードがあれば GPU 版）、ウィンドウを開かずに起動して、セットアップページを開きます。以降、AI は tarjim のツールを直接使います。たとえば「このリンクをフランス語に翻訳して字幕を焼き込んで」「翻訳には私の Claude のサブスクリプションを使って」「ローカルモデルに切り替えて」といった具合です。tarjim は AI が操作するツールであり、話しかける相手となる別のアシスタントではありません。プラグインには [uv](https://docs.astral.sh/uv/) が必要です。

その他の MCP アプリ（Codex、Cursor など）: エンジンのインストール後、コマンド `tarjim-mcp` を MCP サーバーとして追加します。例: `codex mcp add tarjim -- tarjim-mcp`。Codex はツールの呼び出しごとに承認を求めます。確認なしで tarjim のツールを実行させるには、`~/.codex/config.toml` の `[mcp_servers.tarjim]` の下に `default_tools_approval_mode = "approve"` を追加してください。

動作確認済み: プラグインを入れた Claude Code のセッションで、設定の読み取り、用語集の設定、YouTube リンクのスペイン語への翻訳と字幕の返却ができました。Codex（ChatGPT プラン）では設定の読み取りと用語集の設定ができました。ChatGPT の Web サイトとデスクトップアプリは、現時点ではあなたのコンピューター上のツールにアクセスできません（リモートの MCP サーバーしか受け付けないため）。ChatGPT で使う場合は Codex を利用してください。

## 手動でインストール（Windows）

Python 3.11 と、ローカルモデル用に約 10 GB のディスク容量が必要です。

```powershell
git clone https://github.com/willynilly0085-creator/tarjim
cd tarjim
python -m venv .venv
# NVIDIA graphics card: install the CUDA build of PyTorch first (the default one is CPU only)
.venv\Scripts\python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python -m pip install -e ".[dub]"
.venv\Scripts\tarjim-serve
```

<http://127.0.0.1:17653> を開きます。セットアップページがデバイスを確認し、AI に接続し、ffmpeg を含む必要なものをダウンロードします（Windows では ffmpeg をダウンロードし、公開されている SHA-256 と照合します）。使えるグラフィックカードがなくても、処理が遅くなるだけで、すべてプロセッサー上で動作します。

**macOS と Linux** でも手順は同じで、`.venv/bin/...` を使い、加えて `brew install ffmpeg` または `sudo apt install ffmpeg` を実行します。これらのプラットフォームはまだテストされていません。

### ブラウザー拡張機能

tarjim はブラウザーの中で動きます。任意の動画やリンクを右クリックして **ترجم للعربية**（またはあなたの言語）を選び、字幕、焼き込み字幕、吹き替えのいずれかを選びます。ポップアップには各ジョブの進行段階が表示され、一時停止、キャンセル、結果を開くといった操作ができます。

Chrome で `chrome://extensions` を開き、**Developer mode**（デベロッパー モード）をオンにして、**Load unpacked**（パッケージ化されていない拡張機能を読み込む）を選び、`~/.tarjim/extension` フォルダーを指定します。拡張機能は自動でペアリングされます。tarjim のページで **Allow**（許可）を押してください。

### チャット

セットアップページの「チャットから tarjim を使う」のステップで、Claude アプリ、Claude Code、Codex の横にある **Add**（追加）を押します。これで AI がツール全体をあなたの代わりに操作できるようになります:

- 「このリンクをアラビア語に翻訳して吹き替えて」「今どの段階？」「一時停止して」「結果を開いて」;
- 設定の変更: 「翻訳には私の Claude のサブスクリプションを使って」「ローカルモデルに切り替えて」「接続できる AI を一覧にして」「インターフェースを英語にして」;
- 完成した字幕の読み上げ、失敗したジョブの再試行、不足しているツールのダウンロード。

キーがチャット経由で入力されることは決してありません。その場合、AI は tarjim のページを開きます。

### コマンドライン

```bash
tarjim video.mp4                 # Arabic (Saudi), burned into the video
tarjim video.mp4 --to fr         # any target language
tarjim video.mp4 --no-burn       # .srt and .ass only
```

## プライバシーとセキュリティ

- **キー** は OS の暗号化された保管庫（Windows Credential Manager、macOS Keychain、Secret Service）に保存されます。設定ファイルにはキーは一切含まれません。
- **デバイスの外に出るもの** は接続方法によって異なります。クリップの音声は選んだ聞き取りプロバイダーに、テキストは選んだ翻訳・音声プロバイダーに送られます。ローカルモードでは何も外に出ません。これは、吹き替えを含むローカルジョブ全体の実行中にすべての接続を監視して計測したものです（外部接続はゼロ）。モデルはオフラインで読み込まれ、インターネットはツールをダウンロードするときにしか使われません。
- **ローカルサーバー** は 127.0.0.1 でのみ待ち受けます。すべてのリクエストにはトークンまたはページの same-site Cookie が必要で、外部の `Host` ヘッダーは拒否され（DNS リバインディング対策）、Web サイトからはアクセスもペアリング要求もできず、自身のフォルダー以外のファイルは一切配信しません。

問題を報告するには [SECURITY.md](SECURITY.md) を参照してください。

## モデルのライセンス

tarjim のコードにはモデルの重みは含まれていません。モデルは各所有者から直接ダウンロードします。一部のモデルは **商用利用が許可されていません**:

| ツール | ライセンス | 商用利用 |
|---|---|---|
| タイミング整列 `MahmoudAshraf/mms-300m-1130-forced-aligner`（必須） | CC-BY-NC-4.0 | 不可 |
| 音声クローン VoxCPM2（任意） | Apache-2.0 | 可 |
| ローカル翻訳 `aya-expanse:8b`（任意） | CC-BY-NC-4.0 | 不可 |
| ローカル聞き取り Qwen3-ASR-1.7B と Qwen3-ForcedAligner | Apache-2.0 | 可 |
| ffmpeg（LGPL ビルド） | LGPL-2.1 | 可 |

セットアップページでは、各ダウンロードの横にそのライセンスが表示されます。

## ステータス

RTX 5080 を搭載した Windows 11 と、グラフィック支援なしのクリーンインストールでテスト済みです。対象: リンクとファイル、焼き込み字幕と `.srt`、フランス語とアラビア語、一時停止・再開・キャンセル・再試行、3 つの接続方法（Claude と ChatGPT のサブスクリプション、ローカルの Ollama）、チャットツール、上記のセキュリティチェック。未テスト: macOS、Linux、GitHub Copilot と Antigravity のサブスクリプション。

## ライセンス

tarjim は企業を含め、誰でも無料で使えます。どのような目的でも、使用、研究、変更、共有ができます。唯一認められていないのは **販売** です。tarjim そのものを販売することも、tarjim から価値を得ている製品やサービス（ホスティングや有償サポートを含む）を販売することも、誰にも認められていません。[LICENSE.md](LICENSE.md)（Apache License 2.0 と Commons Clause の要約）を参照してください。法的拘束力のある全文（英語）は [../../LICENSE](../../LICENSE) にあります。

tarjim がダウンロードするモデルにはそれぞれ独自のライセンスがあり、その一部は商用利用を禁止しています。それらのモデルを仕事で使う前に、上記のモデルのライセンス表を確認してください。

## 開発

```bash
pip install -e ".[dub,dev]"
pytest && ruff check tarjim tests && mypy tarjim
```

設計上の判断と計測結果は [docs/decisions.md](../../docs/decisions.md) に記録されています。
[CONTRIBUTING.md](CONTRIBUTING.md) も参照してください。
