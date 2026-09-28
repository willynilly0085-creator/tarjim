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
