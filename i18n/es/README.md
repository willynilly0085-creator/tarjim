# tarjim
<!-- languages -->
[English](../../README.md) · [العربية](../../i18n/ar/README.md) · **Español** · [Français](../../i18n/fr/README.md) · [Português](../../i18n/pt/README.md) · [Deutsch](../../i18n/de/README.md) · [Русский](../../i18n/ru/README.md) · [Türkçe](../../i18n/tr/README.md) · [हिन्दी](../../i18n/hi/README.md) · [اردو](../../i18n/ur/README.md) · [Bahasa Indonesia](../../i18n/id/README.md) · [日本語](../../i18n/ja/README.md) · [中文](../../i18n/zh/README.md) · [한국어](../../i18n/ko/README.md)

**Subtítulos y doblaje para cualquier vídeo, en tu idioma, en tu propio ordenador.**

Pega un enlace o suelta un archivo. tarjim escucha, sincroniza cada línea con el momento exacto en
que se dice, distingue a cada hablante, traduce a un lenguaje natural y graba los subtítulos en el
vídeo, genera un `.srt` o lo dobla con una voz distinta para cada hablante.

## Qué hace

- **Cualquier fuente:** enlaces de YouTube, X y otros sitios (yt-dlp), o cualquier archivo de vídeo o audio de tu dispositivo.
- **34 idiomas de destino**, de derecha a izquierda y de izquierda a derecha. El árabe usa por
  defecto un dialecto saudí; el árabe estándar moderno está a un clic.
- **Escucha cuidadosa:** el audio se escucha tres veces y cada palabra se somete a votación, de modo
  que un error de escucha aislado no llega al subtítulo.
- **Sincronización exacta:** las palabras se alinean con el audio en tu ordenador (alineación
  forzada CTC más detección de actividad de voz). Los subtítulos nunca se extienden más allá de un
  cambio de plano hasta el plano de la siguiente persona.
- **Atento a los hablantes:** líneas de diálogo con guiones, una línea por hablante.
- **Doblaje:** una voz natural de Gemini por hablante (elegida según el tono), un clon de voz local
  de cada hablante (VoxCPM2), voces de estudio o Fish Audio. Un guion de voz aparte escribe los
  nombres tal como se pronuncian y los números en letras, para que la voz los diga correctamente.
- **Tres formas de usarlo:** un menú contextual en el navegador ("ترجم للعربية"), una página web
  local o un chat: añade tarjim a la app de Claude, a Claude Code o a Codex y pídele que traduzca un enlace.

## Conecta una IA: tres formas

| Forma | Opciones | Notas |
|---|---|---|
| Clave de API | Gemini, OpenAI, Anthropic, OpenRouter, DeepSeek, Qwen, Mistral, Groq, xAI o cualquier dirección compatible con OpenAI | Gemini y OpenAI también pueden escuchar (voz a texto). |
| Tu suscripción | Claude (a través de Claude Code), ChatGPT (a través de Codex), GitHub Copilot, Google AI (a través de Antigravity) | tarjim ejecuta el propio programa del proveedor con tu sesión iniciada. El uso se descuenta de tu plan y se aplican las condiciones de cada proveedor. |
| En tu ordenador | Ollama, LM Studio, Jan, llama.cpp, vLLM, KoboldCpp | Se detectan automáticamente junto con sus modelos. Nada sale de tu dispositivo. |

Elige cualquier modelo que ofrezca un proveedor. Si el motor elegido falla o agota su cuota, tarjim
recurre al motor local cuando hay uno disponible.

## Instalación con tu IA (un solo paso)

En Claude Code:

```bash
claude plugin marketplace add willynilly0085-creator/tarjim
claude plugin install tarjim@tarjim
```

Después dile a tu IA "configura tarjim". Instala el motor en segundo plano (la versión para tarjeta
gráfica si tienes una tarjeta NVIDIA), lo inicia sin abrir ninguna ventana y abre la página de
configuración. A partir de ahí, tu IA usa directamente las herramientas de tarjim: "traduce este
enlace al francés y graba los subtítulos", "usa mi suscripción de Claude para traducir", "cambia al
modelo local". tarjim es una herramienta que maneja tu IA, no otro asistente con el que conversar.
El plugin necesita [uv](https://docs.astral.sh/uv/).

Otras apps compatibles con MCP (Codex, Cursor y más): una vez instalado el motor, añade el comando
`tarjim-mcp` como servidor MCP, por ejemplo `codex mcp add tarjim -- tarjim-mcp`. Codex te pide
aprobar cada llamada a una herramienta; para que las herramientas de tarjim se ejecuten sin
preguntar, añade `default_tools_approval_mode = "approve"` bajo `[mcp_servers.tarjim]` en
`~/.codex/config.toml`.

Probado: una sesión de Claude Code con el plugin leyó la configuración, definió el glosario, tradujo
un enlace de YouTube al español y devolvió los subtítulos; Codex (plan de ChatGPT) leyó la
configuración y definió el glosario. El sitio web y la app de escritorio de ChatGPT todavía no
pueden acceder a herramientas de tu ordenador (solo aceptan servidores MCP remotos), así que usa
Codex para ChatGPT.

## Instalación manual (Windows)

Requiere Python 3.11 y unos 10 GB de disco para los modelos locales.

```powershell
git clone https://github.com/willynilly0085-creator/tarjim
cd tarjim
python -m venv .venv
# NVIDIA graphics card: install the CUDA build of PyTorch first (the default one is CPU only)
.venv\Scripts\python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128
.venv\Scripts\python -m pip install -e ".[dub]"
.venv\Scripts\tarjim-serve
```

Abre <http://127.0.0.1:17653>. La página de configuración revisa tu dispositivo, conecta una IA y
descarga lo que necesitas, incluido ffmpeg (en Windows se descarga y se verifica con su SHA-256
publicado). Sin una tarjeta gráfica utilizable todo sigue funcionando en el procesador, solo que
más despacio.

**macOS y Linux** siguen los mismos pasos con `.venv/bin/...`, además de `brew install ffmpeg` o
`sudo apt install ffmpeg`. Estas plataformas aún no se han probado.

### Extensión del navegador

tarjim vive en tu navegador: haz clic derecho en cualquier vídeo o enlace y elige **ترجم للعربية**
(o tu idioma), y luego elige subtítulos, subtítulos grabados o doblaje. La ventana emergente muestra
la etapa de cada trabajo y te permite pausarlo, cancelarlo o abrir el resultado.

En Chrome abre `chrome://extensions`, activa **Developer mode** (modo de desarrollador), elige
**Load unpacked** (cargar descomprimida) y selecciona la carpeta `~/.tarjim/extension`. La extensión se
empareja sola: pulsa **Allow** (permitir) en la página de tarjim.

### Chat

En la página de configuración, en el paso "Use tarjim from a chat" (usar tarjim desde un chat),
pulsa **Add** (añadir) junto a la app de Claude, Claude Code o Codex. A partir de entonces tu IA
puede manejar toda la herramienta por ti:

- "Traduce este enlace al árabe y dóblalo", "¿en qué etapa va?", "ponlo en pausa", "abre el resultado";
- cambiar la configuración: "usa mi suscripción de Claude para traducir", "cambia al modelo local",
  "enumera las IA que puedo conectar", "pon la interfaz en inglés";
- leerte los subtítulos terminados, reintentar un trabajo fallido o descargar una herramienta que falte.

Las claves nunca se introducen por el chat; para eso la IA abre la página de tarjim.

### Línea de comandos

```bash
tarjim video.mp4                 # Arabic (Saudi), burned into the video
tarjim video.mp4 --to fr         # any target language
tarjim video.mp4 --no-burn       # .srt and .ass only
```

## Privacidad y seguridad

- **Las claves** se guardan en el almacén cifrado de tu sistema operativo (Administrador de
  credenciales de Windows, Llavero de macOS, Secret Service). El archivo de configuración no
  contiene ninguna.
- **Lo que sale de tu dispositivo** depende de cómo te conectes: el audio del clip va al proveedor
  de escucha que elegiste, y el texto va a los proveedores de traducción y de voz que elegiste. En
  modo local no sale nada: se midió observando cada conexión durante un trabajo local completo,
  doblaje incluido (cero conexiones externas). Los modelos se cargan sin conexión; internet solo se
  usa cuando descargas una herramienta.
- **El servidor local** escucha solo en 127.0.0.1. Cada solicitud necesita un token o la cookie
  same-site de la página, se rechazan las cabeceras `Host` ajenas (DNS rebinding), los sitios web no
  pueden acceder a él ni pedir emparejarse, y no sirve ningún archivo fuera de sus propias carpetas.

Consulta [SECURITY.md](SECURITY.md) para informar de un problema.

## Licencias de los modelos

El código de tarjim no incluye los pesos de los modelos; los descargas de sus propietarios. Algunos
**no tienen licencia para uso comercial**:

| Herramienta | Licencia | Uso comercial |
|---|---|---|
| Alineador de sincronización `MahmoudAshraf/mms-300m-1130-forced-aligner` (obligatorio) | CC-BY-NC-4.0 | No |
| Clon de voz VoxCPM2 (opcional) | Apache-2.0 | Sí |
| Traducción local `aya-expanse:8b` (opcional) | CC-BY-NC-4.0 | No |
| Escucha local Qwen3-ASR-1.7B y Qwen3-ForcedAligner | Apache-2.0 | Sí |
| ffmpeg (compilación LGPL) | LGPL-2.1 | Sí |

La página de configuración muestra cada licencia junto a su descarga.

## Estado

Probado en Windows 11 con una RTX 5080, y desde una instalación limpia sin soporte gráfico: enlaces
y archivos, subtítulos grabados y `.srt`, francés y árabe, pausar, reanudar, cancelar y reintentar,
las tres formas de conexión (suscripciones de Claude y ChatGPT, Ollama local), las herramientas de
chat y las comprobaciones de seguridad anteriores. Aún sin probar: macOS, Linux y las suscripciones
de GitHub Copilot y Antigravity.

## Licencia

tarjim es gratuito para todos, empresas incluidas: úsalo, estúdialo, modifícalo y compártelo, con
cualquier fin. Lo único que no está permitido es **venderlo**: nadie puede vender tarjim, ni vender
un producto o servicio (incluidos el alojamiento y el soporte de pago) cuyo valor provenga de
tarjim. Consulta [LICENSE.md](LICENSE.md); el texto completo y vinculante, en inglés, está en
[../../LICENSE](../../LICENSE) (Apache License 2.0 con la Commons Clause).

Los modelos que descarga tarjim tienen sus propias licencias, y algunas prohíben el uso comercial:
revisa la tabla de licencias de los modelos de arriba antes de usarlos para trabajar.

## Desarrollo

```bash
pip install -e ".[dub,dev]"
pytest && ruff check tarjim tests && mypy tarjim
```

Las decisiones de diseño y las mediciones se registran en [docs/decisions.md](../../docs/decisions.md).
Consulta [CONTRIBUTING.md](CONTRIBUTING.md).
