# Segurança
<!-- languages -->
[English](../../SECURITY.md) · [العربية](../../i18n/ar/SECURITY.md) · [Español](../../i18n/es/SECURITY.md) · [Français](../../i18n/fr/SECURITY.md) · **Português** · [Deutsch](../../i18n/de/SECURITY.md) · [Русский](../../i18n/ru/SECURITY.md) · [Türkçe](../../i18n/tr/SECURITY.md) · [हिन्दी](../../i18n/hi/SECURITY.md) · [اردو](../../i18n/ur/SECURITY.md) · [Bahasa Indonesia](../../i18n/id/SECURITY.md) · [日本語](../../i18n/ja/SECURITY.md) · [中文](../../i18n/zh/SECURITY.md) · [한국어](../../i18n/ko/SECURITY.md)

## Como relatar um problema

Relate problemas de segurança de forma privada pelo botão **Report a vulnerability** (relatar uma
vulnerabilidade) do GitHub neste repositório, e não em uma issue pública. Descreva o que você
encontrou, como reproduzir e o que isso permite que alguém faça. Os relatos são lidos e respondidos
o mais rápido possível.

## O que o tarjim protege

- **As chaves e o token de pareamento** ficam no cofre criptografado do sistema operacional, por
  meio do `keyring`. Nunca aparecem no arquivo de configurações, nas respostas do servidor, nos
  logs nem nas ferramentas de chat.
- **O servidor local** (`tarjim-serve`) escuta apenas em 127.0.0.1 e recusa:
  - requisições sem o token (`X-Tarjim-Token`) ou sem o cookie HttpOnly, SameSite=Strict da página;
  - requisições cujo `Host` não é local (DNS rebinding);
  - pedidos de pareamento que não vêm de uma extensão do navegador;
  - qualquer caminho fora da própria pasta web e dos resultados concluídos de uma tarefa.
- **As assinaturas** são usadas executando o próprio programa do fornecedor (Claude Code, Codex,
  Copilot, Antigravity). O tarjim nunca lê nem guarda os arquivos de login ou os tokens deles.
- **O modo local** mantém a mídia no dispositivo: os modelos carregam com o hub do Hugging Face
  offline, e a rede só é usada durante o download de uma ferramenta que a pessoa pediu.
- **Downloads**: o ffmpeg é conferido com o SHA-256 publicado junto com a versão dele.

## Limites conhecidos

- Qualquer pessoa que consiga executar programas com o seu usuário no seu computador pode ler o
  cofre e o token. O tarjim não protege contra uma conta comprometida.
- Os provedores de nuvem que você escolher recebem o áudio ou o texto que processam, sob os
  próprios termos.

## Problemas conhecidos nas bibliotecas

Vulnerabilidades publicadas em bibliotecas que o tarjim instala e que nenhuma versão testada consegue evitar ainda: nenhuma no momento. Se surgir alguma, seus dados vêm com o tarjim em `tarjim/known_issues.json`: **Configurações**, a resposta `/update` do motor e o `setup_status` das ferramentas de chat a mostram nos computadores cuja versão instalada é afetada, e ela some sozinha quando uma atualização instala uma versão corrigida. O CI falha com qualquer vulnerabilidade que não esteja aqui, e uma verificação semanal avisa quando uma da lista pode ser corrigida.

**Fechadas em 2026-10-23.** Seis avisos do transformers (PYSEC-2025-217, PYSEC-2026-2288, PYSEC-2026-2289, PYSEC-2026-2290, PYSEC-2026-3929, PYSEC-2026-4174) ficaram abertos enquanto o qwen-asr, o mecanismo de escuta local da época, prendia o transformers na 4.57.6. A escuta local agora usa os modelos Qwen3-ASR do próprio Transformers, então o tarjim instala o transformers 5.20.2 e não instala mais o qwen-asr; o accelerate continua na 1.15.0 (PYSEC-2026-3804 fechada) sem nenhuma exceção.

**O que o tarjim faz em qualquer caso.** Cada modelo do Hugging Face é baixado de um commit fixo (`tarjim/model_pins.py`), só suas configurações, tokenizador, modelo de chat e arquivos safetensors, nunca código; seus arquivos grandes precisam bater com o SHA-256 publicado, e ele é carregado dessa pasta no computador com o hub offline. `trust_remote_code` nunca é ativado, e o pacote `kernels` não é instalado. Os pesos de separação de voz só carregam se nomearem a classe de modelo do próprio demucs, e o modelo de diacríticos só se os dois arquivos baterem com o SHA-256 da sua versão.
