# tarjim
<!-- languages -->
[English](../../README.md) · [العربية](../../i18n/ar/README.md) · [Español](../../i18n/es/README.md) · [Français](../../i18n/fr/README.md) · [Português](../../i18n/pt/README.md) · [Deutsch](../../i18n/de/README.md) · [Русский](../../i18n/ru/README.md) · [Türkçe](../../i18n/tr/README.md) · [हिन्दी](../../i18n/hi/README.md) · [اردو](../../i18n/ur/README.md) · [Bahasa Indonesia](../../i18n/id/README.md) · [日本語](../../i18n/ja/README.md) · [中文](../../i18n/zh/README.md) · **한국어**

**어떤 동영상이든, 여러분의 언어로 자막과 더빙을. 모두 여러분의 컴퓨터에서.**

링크를 붙여 넣거나 파일을 끌어다 놓기만 하면 됩니다. tarjim은 음성을 듣고, 각 줄을 말하는 순간에 정확히 맞추고, 화자를 하나하나 구분하고, 자연스러운 구어체로 번역합니다. 그런 다음 자막을 동영상에 입히거나, `.srt` 파일을 만들거나, 화자마다 목소리를 따로 입혀 더빙합니다.

## 주요 기능

- **모든 소스 지원:** YouTube, X 등의 링크(yt-dlp) 또는 기기에 있는 모든 동영상·오디오 파일.
- **34개 대상 언어**, 오른쪽에서 왼쪽으로 쓰는 언어와 왼쪽에서 오른쪽으로 쓰는 언어 모두 지원. 아랍어는 사우디 방언이 기본이며, 클릭 한 번으로 현대 표준 아랍어로 바꿀 수 있습니다.
- **꼼꼼한 음성 인식:** 오디오를 세 번 듣고 모든 단어를 투표로 결정하므로, 한 번 잘못 들은 내용이 자막에 남지 않습니다.
- **정확한 타이밍:** 단어를 여러분의 컴퓨터에서 오디오에 맞춰 정렬합니다(CTC 강제 정렬과 음성 구간 검출). 자막이 장면 전환을 넘어 다음 인물의 장면까지 이어지는 일은 없습니다.
- **화자 인식:** 대화는 대시로 구분하며, 화자마다 한 줄씩 표시합니다.
- **더빙:** 화자별 자연스러운 Gemini 음성(음높이로 매칭), 각 화자의 로컬 음성 복제(XTTS-v2), 스튜디오 음성 또는 Fish Audio 중에서 고를 수 있습니다. 별도의 음성용 스크립트가 이름은 실제 발음대로, 숫자는 글로 풀어 쓰기 때문에 음성이 정확하게 읽습니다.
- **세 가지 사용 방법:** 브라우저의 마우스 오른쪽 버튼 메뉴("ترجم للعربية"), 로컬 웹 페이지, 또는 채팅. Claude 앱, Claude Code, Codex에 tarjim을 추가하고 링크 번역을 요청하면 됩니다.

## AI 연결: 세 가지 방법

| 방법 | 선택지 | 참고 |
|---|---|---|
| API 키 | Gemini, OpenAI, Anthropic, OpenRouter, DeepSeek, Qwen, Mistral, Groq, xAI 또는 모든 OpenAI 호환 주소 | Gemini와 OpenAI는 음성 인식(음성을 텍스트로 변환)에도 쓸 수 있습니다. |
| 사용 중인 구독 | Claude(Claude Code를 통해), ChatGPT(Codex를 통해), GitHub Copilot, Google AI(Antigravity를 통해) | tarjim은 여러분의 로그인 정보로 각 공급업체의 자체 프로그램을 실행합니다. 사용량은 여러분의 요금제에서 차감되며 각 공급업체의 약관이 적용됩니다. |
| 내 컴퓨터에서 | Ollama, LM Studio, Jan, llama.cpp, vLLM, KoboldCpp | 모델과 함께 자동으로 감지됩니다. 어떤 데이터도 기기 밖으로 나가지 않습니다. |

공급업체가 제공하는 모델이라면 무엇이든 고를 수 있습니다. 선택한 엔진이 실패하거나 할당량이 소진되면, 로컬 엔진이 있는 경우 tarjim이 자동으로 로컬 엔진으로 전환합니다.

## AI로 설치하기(한 단계)

Claude Code에서:

```bash
claude plugin marketplace add willynilly0085-creator/tarjim
claude plugin install tarjim@tarjim
```

그다음 AI에게 "tarjim 설정해 줘"라고 말하세요. AI가 백그라운드에서 엔진을 설치하고(NVIDIA 그래픽 카드가 있으면 그래픽 카드용 빌드), 창을 띄우지 않고 실행한 뒤 설정 페이지를 엽니다. 그 뒤로는 AI가 tarjim의 도구를 직접 사용합니다. 예를 들어 "이 링크를 프랑스어로 번역하고 자막을 입혀 줘", "번역에는 내 Claude 구독을 써 줘", "로컬 모델로 바꿔 줘"처럼 말하면 됩니다. tarjim은 AI가 다루는 도구이지, 따로 대화해야 하는 또 하나의 어시스턴트가 아닙니다. 플러그인을 쓰려면 [uv](https://docs.astral.sh/uv/)가 필요합니다.

다른 MCP 앱(Codex, Cursor 등): 엔진을 설치한 뒤 `tarjim-mcp` 명령을 MCP 서버로 추가하세요. 예: `codex mcp add tarjim -- tarjim-mcp`. Codex는 도구를 호출할 때마다 승인을 요청합니다. 묻지 않고 tarjim의 도구를 실행하게 하려면 `~/.codex/config.toml`의 `[mcp_servers.tarjim]` 아래에 `default_tools_approval_mode = "approve"`를 추가하세요.

테스트 완료: 플러그인을 설치한 Claude Code 세션에서 설정을 읽고, 용어집을 설정하고, YouTube 링크를 스페인어로 번역해 자막을 돌려받았습니다. Codex(ChatGPT 요금제)에서는 설정을 읽고 용어집을 설정했습니다. ChatGPT 웹사이트와 데스크톱 앱은 아직 여러분의 컴퓨터에 있는 도구에 접근할 수 없으므로(원격 MCP 서버만 지원), ChatGPT를 쓰려면 Codex를 이용하세요.

## 직접 설치하기(Windows)

Python 3.11과 로컬 모델용으로 약 10 GB의 디스크 공간이 필요합니다.

```powershell
git clone https://github.com/willynilly0085-creator/tarjim
cd tarjim
python -m venv .venv
# NVIDIA graphics card: install the CUDA build of PyTorch first (the default one is CPU only)
.venv\Scripts\python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python -m pip install -e ".[dub]"
.venv\Scripts\tarjim-serve
```

<http://127.0.0.1:17653>을 여세요. 설정 페이지가 기기를 확인하고, AI를 연결하고, ffmpeg을 포함해 필요한 것을 내려받습니다(Windows에서는 ffmpeg을 내려받은 뒤 공개된 SHA-256과 대조해 검증합니다). 쓸 수 있는 그래픽 카드가 없어도 모든 기능이 프로세서에서 동작하며, 속도만 느려집니다.

**macOS와 Linux**도 같은 단계를 따르되 `.venv/bin/...`을 사용하고, 추가로 `brew install ffmpeg` 또는 `sudo apt install ffmpeg`을 실행합니다. 이 플랫폼들은 아직 테스트되지 않았습니다.

### 브라우저 확장 프로그램

tarjim은 브라우저 안에 있습니다. 동영상이나 링크를 마우스 오른쪽 버튼으로 클릭하고 **ترجم للعربية**(또는 여러분의 언어)를 선택한 다음, 자막, 입힌 자막, 더빙 중 하나를 고르세요. 팝업에는 각 작업의 진행 단계가 표시되며, 일시 중지, 취소, 결과 열기를 할 수 있습니다.

Chrome에서 `chrome://extensions`를 열고 **Developer mode**(개발자 모드)를 켠 뒤, **Load unpacked**(압축해제된 확장 프로그램을 로드합니다)를 선택하고 `extension` 폴더를 지정하세요. 확장 프로그램은 스스로 페어링됩니다. tarjim 페이지에서 **Allow**(허용)를 누르세요.

### 채팅

설정 페이지의 "채팅에서 tarjim 사용하기" 단계에서 Claude 앱, Claude Code 또는 Codex 옆에 있는 **Add**(추가)를 누르세요. 그러면 AI가 여러분 대신 도구 전체를 다룰 수 있습니다:

- "이 링크를 아랍어로 번역하고 더빙해 줘", "지금 어느 단계야?", "일시 중지해 줘", "결과 열어 줘";
- 설정 변경: "번역에는 내 Claude 구독을 써 줘", "로컬 모델로 바꿔 줘", "연결할 수 있는 AI 목록 보여 줘", "인터페이스를 영어로 바꿔 줘";
- 완성된 자막 읽어 주기, 실패한 작업 다시 시도하기, 빠진 도구 내려받기.

키는 절대 채팅으로 입력하지 않습니다. 이때는 AI가 tarjim 페이지를 열어 줍니다.

### 명령줄

```bash
tarjim video.mp4                 # Arabic (Saudi), burned into the video
tarjim video.mp4 --to fr         # any target language
tarjim video.mp4 --no-burn       # .srt and .ass only
```

## 개인정보 보호와 보안

- **키**는 운영체제의 암호화된 보관소(Windows Credential Manager, macOS Keychain, Secret Service)에 저장됩니다. 설정 파일에는 키가 전혀 들어 있지 않습니다.
- **기기 밖으로 나가는 데이터**는 연결 방식에 따라 다릅니다. 클립의 오디오는 여러분이 고른 음성 인식 공급업체로, 텍스트는 여러분이 고른 번역·음성 공급업체로 전송됩니다. 로컬 모드에서는 아무것도 나가지 않습니다. 이는 더빙을 포함한 전체 로컬 작업 동안 모든 연결을 지켜보며 측정한 결과입니다(외부 연결 0건). 모델은 오프라인으로 로드되며, 인터넷은 도구를 내려받을 때만 사용됩니다.
- **로컬 서버**는 127.0.0.1에서만 수신합니다. 모든 요청에는 토큰이나 페이지의 same-site 쿠키가 필요하고, 외부 `Host` 헤더는 거부되며(DNS 리바인딩 방지), 웹사이트는 서버에 접근하거나 페어링을 요청할 수 없고, 서버는 자신의 폴더 밖에 있는 파일을 제공하지 않습니다.

문제를 신고하려면 [SECURITY.md](SECURITY.md)를 참고하세요.

## 모델 라이선스

tarjim의 코드에는 모델 가중치가 포함되어 있지 않으며, 모델은 각 소유자에게서 직접 내려받습니다. 일부 모델은 **상업적 사용이 허가되지 않습니다**:

| 도구 | 라이선스 | 상업적 사용 |
|---|---|---|
| 타이밍 정렬기 `MahmoudAshraf/mms-300m-1130-forced-aligner`(필수) | CC-BY-NC-4.0 | 불가 |
| 음성 복제 XTTS-v2(선택, 동의를 구함) | Coqui Public Model License | 불가 |
| 로컬 번역 `aya-expanse:8b`(선택) | CC-BY-NC-4.0 | 불가 |
| 로컬 음성 인식 Qwen3-ASR-1.7B 및 Qwen3-ForcedAligner | Apache-2.0 | 가능 |
| ffmpeg(LGPL 빌드) | LGPL-2.1 | 가능 |

설정 페이지는 각 다운로드 항목 옆에 해당 라이선스를 표시합니다.

## 현황

RTX 5080이 장착된 Windows 11과, 그래픽 지원이 없는 새로 설치한 환경에서 테스트했습니다. 테스트 범위: 링크와 파일, 입힌 자막과 `.srt`, 프랑스어와 아랍어, 일시 중지·재개·취소·재시도, 세 가지 연결 방법(Claude와 ChatGPT 구독, 로컬 Ollama), 채팅 도구, 위의 보안 점검. 아직 테스트하지 않은 항목: macOS, Linux, GitHub Copilot 및 Antigravity 구독.

## 라이선스

tarjim은 기업을 포함해 누구에게나 무료입니다. 어떤 목적으로든 사용하고, 연구하고, 수정하고, 공유할 수 있습니다. 허용되지 않는 것은 단 하나, **판매**입니다. 누구도 tarjim을 판매하거나, tarjim에서 가치가 나오는 제품이나 서비스(호스팅과 유료 지원 포함)를 판매할 수 없습니다. [LICENSE.md](LICENSE.md)(Apache License 2.0 및 Commons Clause 요약)를 참고하세요. 법적 구속력이 있는 전문(영어)은 [../../LICENSE](../../LICENSE)에 있습니다.

tarjim이 내려받는 모델에는 각각 고유한 라이선스가 있으며, 그중 일부는 상업적 사용을 금지합니다. 이런 모델을 업무에 사용하기 전에 위의 모델 라이선스 표를 확인하세요.

## 개발

```bash
pip install -e ".[dub,dev]"
pytest && ruff check tarjim tests && mypy tarjim
```

설계 결정과 측정 결과는 [docs/decisions.md](../../docs/decisions.md)에 기록되어 있습니다.
[CONTRIBUTING.md](CONTRIBUTING.md)도 참고하세요.
