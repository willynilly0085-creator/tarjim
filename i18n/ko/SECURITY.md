# 보안
<!-- languages -->
[English](../../SECURITY.md) · [العربية](../../i18n/ar/SECURITY.md) · [Español](../../i18n/es/SECURITY.md) · [Français](../../i18n/fr/SECURITY.md) · [Português](../../i18n/pt/SECURITY.md) · [Deutsch](../../i18n/de/SECURITY.md) · [Русский](../../i18n/ru/SECURITY.md) · [Türkçe](../../i18n/tr/SECURITY.md) · [हिन्दी](../../i18n/hi/SECURITY.md) · [اردو](../../i18n/ur/SECURITY.md) · [Bahasa Indonesia](../../i18n/id/SECURITY.md) · [日本語](../../i18n/ja/SECURITY.md) · [中文](../../i18n/zh/SECURITY.md) · **한국어**

## 문제 신고

보안 문제는 공개 이슈가 아니라, 이 저장소에 있는 GitHub의 "Report a vulnerability"(취약점 신고) 버튼을 통해 비공개로 신고해 주세요. 무엇을 발견했는지, 어떻게 재현하는지, 그리고 그것으로 누군가가 무엇을 할 수 있는지를 설명해 주세요. 신고는 가능한 한 빨리 확인하고 답변합니다.

## tarjim이 보호하는 것

- **키와 페어링 토큰**은 `keyring`을 통해 운영체제의 암호화된 보관소에 저장됩니다. 설정 파일, 서버 응답, 로그, 채팅 도구에는 절대 나타나지 않습니다.
- **로컬 서버**(`tarjim-serve`)는 127.0.0.1에서만 수신하며 다음을 거부합니다:
  - 토큰(`X-Tarjim-Token`)도, 페이지의 HttpOnly, SameSite=Strict 쿠키도 없는 요청;
  - `Host`가 로컬이 아닌 요청(DNS 리바인딩);
  - 브라우저 확장 프로그램에서 오지 않은 페어링 요청;
  - 자체 웹 폴더와 작업의 완성된 출력물 밖에 있는 모든 경로.
- **구독**은 각 공급업체의 자체 프로그램(Claude Code, Codex, Copilot, Antigravity)을 실행하는 방식으로 사용합니다. tarjim은 해당 프로그램의 로그인 파일이나 토큰을 절대 읽거나 저장하지 않습니다.
- **로컬 모드**에서는 미디어가 기기 안에 머뭅니다. 모델은 Hugging Face hub를 오프라인으로 둔 상태에서 로드되며, 네트워크는 사용자가 요청한 도구를 내려받는 동안에만 사용됩니다.
- **다운로드**: ffmpeg은 릴리스와 함께 공개된 SHA-256과 대조해 검증합니다.

## 알려진 한계

- 여러분의 컴퓨터에서 여러분의 사용자 계정으로 프로그램을 실행할 수 있는 사람은 보관소와 토큰을 읽을 수 있습니다. tarjim은 탈취된 계정을 방어하지 않습니다.
- 여러분이 선택한 클라우드 공급업체는 처리하는 오디오나 텍스트를 각자의 약관에 따라 받게 됩니다.

## 라이브러리의 알려진 문제

tarjim이 설치하는 라이브러리에 공개된 취약점 중 테스트한 어떤 버전으로도 아직 피할 수 없는 것: 현재는 없습니다. 생기면 그 내용이 tarjim과 함께 `tarjim/known_issues.json`으로 배포됩니다. **설정**, 엔진의 `/update` 응답, 채팅 도구의 `setup_status`가 설치된 버전이 해당하는 컴퓨터에 보여 주고, 업데이트로 수정된 버전이 설치되면 저절로 사라집니다. 여기에 없는 취약점이 있으면 CI가 실패하고, 매주 검사가 목록의 항목을 고칠 수 있게 되면 알려 줍니다.

**2026-10-23에 해결.** 당시 로컬 듣기 엔진이던 qwen-asr가 transformers를 4.57.6에 묶어 두는 동안 transformers 권고 6건(PYSEC-2025-217, PYSEC-2026-2288, PYSEC-2026-2289, PYSEC-2026-2290, PYSEC-2026-3929, PYSEC-2026-4174)이 남아 있었습니다. 이제 로컬 듣기는 Transformers 자체의 Qwen3-ASR 모델로 동작하므로, tarjim은 transformers 5.20.2를 설치하고 qwen-asr는 더 이상 설치하지 않습니다. accelerate는 별도 재정의 없이 1.15.0입니다(PYSEC-2026-3804 해결).

**tarjim이 항상 하는 일.** 모든 Hugging Face 모델은 고정된 커밋(`tarjim/model_pins.py`)에서 내려받고, 설정, 토크나이저, 채팅 템플릿, safetensors 파일만 받으며 코드는 받지 않습니다. 큰 파일은 공개된 SHA-256과 일치해야 하고, 허브를 오프라인으로 둔 채 컴퓨터의 그 폴더에서 불러옵니다. `trust_remote_code`는 절대 쓰지 않고 `kernels` 패키지도 설치하지 않습니다. 음성 분리 가중치는 demucs 자체 모델 클래스를 가리킬 때만, 발음 부호 모델은 두 파일이 릴리스의 SHA-256과 일치할 때만 불러옵니다.
