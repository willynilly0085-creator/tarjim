import asyncio
import io

import numpy as np

from tarjim.dub.audio import decode
from tarjim.dub.lines import Line

VOICES = {
    "ar": ("ar-SA-HamedNeural", "ar-SA-ZariyahNeural"),
    "en": ("en-US-GuyNeural", "en-US-JennyNeural"),
    "fr": ("fr-FR-HenriNeural", "fr-FR-DeniseNeural"),
    "es": ("es-ES-AlvaroNeural", "es-ES-ElviraNeural"),
    "de": ("de-DE-ConradNeural", "de-DE-KatjaNeural"),
    "it": ("it-IT-DiegoNeural", "it-IT-ElsaNeural"),
    "pt": ("pt-BR-AntonioNeural", "pt-BR-FranciscaNeural"),
    "tr": ("tr-TR-AhmetNeural", "tr-TR-EmelNeural"),
    "ru": ("ru-RU-DmitryNeural", "ru-RU-SvetlanaNeural"),
    "ur": ("ur-PK-AsadNeural", "ur-PK-UzmaNeural"),
    "fa": ("fa-IR-FaridNeural", "fa-IR-DilaraNeural"),
    "hi": ("hi-IN-MadhurNeural", "hi-IN-SwaraNeural"),
    "id": ("id-ID-ArdiNeural", "id-ID-GadisNeural"),
    "ja": ("ja-JP-KeitaNeural", "ja-JP-NanamiNeural"),
    "ko": ("ko-KR-InJoonNeural", "ko-KR-SunHiNeural"),
    "zh": ("zh-CN-YunxiNeural", "zh-CN-XiaoxiaoNeural"),
}
PARALLEL = 4


def cast(speakers: list[str], language: str) -> dict[str, str]:
    choices = VOICES[language]
    return {speaker: choices[index % len(choices)] for index, speaker in enumerate(speakers)}


class StudioVoices:
    def __init__(self, speakers: list[str], language: str) -> None:
        self.voices = cast(speakers, language)
        self.fallback = VOICES[language][0]

    async def one(self, line: Line, gate: asyncio.Semaphore) -> bytes:
        import edge_tts

        async with gate:
            buffer = io.BytesIO()
            voice = self.voices.get(line.speaker, self.fallback)
            async for chunk in edge_tts.Communicate(line.text, voice).stream():
                if chunk["type"] == "audio":
                    buffer.write(chunk["data"])
            return buffer.getvalue()

    async def all(self, lines: list[Line]) -> list[bytes]:
        gate = asyncio.Semaphore(PARALLEL)
        return list(await asyncio.gather(*(self.one(line, gate) for line in lines)))

    def speak_all(self, lines: list[Line]) -> list[np.ndarray]:
        blobs = asyncio.run(self.all(lines))
        return [decode(blob) if blob else np.zeros(0, dtype=np.float32) for blob in blobs]
