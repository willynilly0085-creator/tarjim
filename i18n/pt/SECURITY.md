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
