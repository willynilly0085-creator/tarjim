# Seguridad
<!-- languages -->
[English](../../SECURITY.md) · [العربية](../../i18n/ar/SECURITY.md) · **Español** · [Français](../../i18n/fr/SECURITY.md) · [Português](../../i18n/pt/SECURITY.md) · [Deutsch](../../i18n/de/SECURITY.md) · [Русский](../../i18n/ru/SECURITY.md) · [Türkçe](../../i18n/tr/SECURITY.md) · [हिन्दी](../../i18n/hi/SECURITY.md) · [اردو](../../i18n/ur/SECURITY.md) · [Bahasa Indonesia](../../i18n/id/SECURITY.md) · [日本語](../../i18n/ja/SECURITY.md) · [中文](../../i18n/zh/SECURITY.md) · [한국어](../../i18n/ko/SECURITY.md)

## Cómo informar de un problema

Informa de los problemas de seguridad de forma privada mediante el botón **Report a vulnerability**
(informar de una vulnerabilidad) de GitHub en este repositorio, no en una issue pública. Describe lo
que encontraste, cómo reproducirlo y qué permite hacer a alguien. Los informes se leen y se
responden lo antes posible.

## Qué protege tarjim

- **Las claves y el token de emparejamiento** se guardan en el almacén cifrado del sistema operativo
  a través de `keyring`. Nunca aparecen en el archivo de configuración, en las respuestas del
  servidor, en los registros ni en las herramientas de chat.
- **El servidor local** (`tarjim-serve`) escucha solo en 127.0.0.1 y rechaza:
  - las solicitudes sin el token (`X-Tarjim-Token`) o sin la cookie HttpOnly, SameSite=Strict de la página;
  - las solicitudes cuyo `Host` no es local (DNS rebinding);
  - las solicitudes de emparejamiento que no proceden de una extensión del navegador;
  - cualquier ruta fuera de su propia carpeta web y de los resultados terminados de un trabajo.
- **Las suscripciones** se usan ejecutando el propio programa del proveedor (Claude Code, Codex,
  Copilot, Antigravity). tarjim nunca lee ni guarda sus archivos de inicio de sesión ni sus tokens.
- **El modo local** mantiene los archivos multimedia en el dispositivo: los modelos se cargan con el
  hub de Hugging Face sin conexión, y la red solo se usa mientras se descarga una herramienta que la
  persona ha pedido.
- **Descargas**: ffmpeg se verifica con el SHA-256 publicado junto con su versión.

## Límites conocidos

- Cualquiera que pueda ejecutar programas con tu usuario en tu ordenador puede leer el almacén y el
  token. tarjim no protege frente a una cuenta comprometida.
- Los proveedores en la nube que elijas reciben el audio o el texto que procesan, bajo sus propias
  condiciones.
