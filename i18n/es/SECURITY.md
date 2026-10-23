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

## Problemas conocidos en las bibliotecas

Vulnerabilidades publicadas en bibliotecas que instala tarjim y que ninguna versión probada puede evitar todavía: ninguna por ahora. Si aparece alguna, sus datos llegan con tarjim en `tarjim/known_issues.json`: **Ajustes**, la respuesta `/update` del motor y `setup_status` de las herramientas de chat la muestran en los ordenadores cuya versión instalada está afectada, y desaparece sola cuando una actualización instala una versión corregida. CI falla con cualquier vulnerabilidad que no esté aquí, y una revisión semanal avisa cuando una de la lista se puede corregir.

**Cerradas el 2026-10-23.** Seis avisos de transformers (PYSEC-2025-217, PYSEC-2026-2288, PYSEC-2026-2289, PYSEC-2026-2290, PYSEC-2026-3929, PYSEC-2026-4174) siguieron abiertos mientras qwen-asr, el motor de escucha local de entonces, fijaba transformers en 4.57.6. La escucha local usa ahora los modelos Qwen3-ASR propios de Transformers, así que tarjim instala transformers 5.20.2 y ya no instala qwen-asr; accelerate sigue en 1.15.0 (PYSEC-2026-3804 cerrada) sin ninguna excepción.

**Lo que tarjim hace en cualquier caso.** Cada modelo de Hugging Face se descarga de un commit fijo (`tarjim/model_pins.py`), solo sus ajustes, tokenizador, plantilla de chat y archivos safetensors, nunca código; sus archivos grandes deben coincidir con su SHA-256 publicado, y se carga desde esa carpeta del ordenador con el hub sin conexión. `trust_remote_code` nunca se activa y el paquete `kernels` no está instalado. Los pesos de separación de voz solo se cargan si nombran la clase de modelo propia de demucs, y el modelo de diacríticos solo si ambos archivos coinciden con el SHA-256 de su versión.
