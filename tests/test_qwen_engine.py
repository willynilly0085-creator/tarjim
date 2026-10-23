"""Local listening through Transformers' own Qwen3-ASR classes keeps the contract of the engine it
replaced: one Transcript with the language, the text and every word with its start and end, long
sound heard in three-minute pieces put back on one timeline, and the earlier models' weights
loading into the same classes until the native ones are here."""
import types
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import soundfile

from tarjim.asr import pieces, qwen, qwen_run
from tarjim.asr.qwen_run import Loaded, Stamp

RATE = pieces.RATE


class Batch(dict):  # type: ignore[type-arg]
    def to(self, *_where: Any) -> "Batch":
        return self


class FakeProcessor:
    """Stands in for Qwen3ASRProcessor: records what it is given, answers like the real one."""

    def __init__(self, heard: list[str]) -> None:
        self.heard, self.calls, self.split = list(heard), [], []  # type: ignore[var-annotated]

    def __call__(self, text: list[str], audio: list[np.ndarray], **_options: Any) -> Batch:
        self.calls.append((text, [len(a) for a in audio]))
        return Batch(input_ids=np.zeros((len(text), 3), dtype=np.int64))

    def batch_decode(self, rows: Any, **_options: Any) -> list[str]:
        return [self.heard.pop(0) for _ in range(len(rows))]

    def parse_output(self, raw: str) -> dict[str, Any]:
        language, _, text = raw.partition("<asr_text>")
        return {"language": language.removeprefix("language ") or None, "transcription": text}

    def split_words_for_alignment(self, text: str, language: str | None) -> list[str]:
        self.split.append(language)
        return [w.strip(".,!?") for w in text.split()]

    def decode_forced_alignment(self, word_lists: list[list[str]], **_options: Any) -> list[Any]:
        return [[{"text": w, "start_time": k * 1.0, "end_time": k + 0.5} for k, w in enumerate(ws)]
                for ws in word_lists]


def fake(heard: list[str]) -> Loaded:
    model = types.SimpleNamespace(device=types.SimpleNamespace(type="cpu"), dtype="float32",
                                  generate=lambda **inputs: np.zeros((len(inputs["input_ids"]), 5)))
    return Loaded(model, FakeProcessor(heard))


class Aligner:
    def __init__(self) -> None:
        self.processor = FakeProcessor([])
        self.model = self

    device = types.SimpleNamespace(type="cpu")
    dtype = "float32"
    config = types.SimpleNamespace(timestamp_token_id=7)

    def __call__(self, **_inputs: Any) -> Any:
        return types.SimpleNamespace(logits=None)


def engine(heard: list[str], monkeypatch: pytest.MonkeyPatch) -> qwen.QwenEngine:
    monkeypatch.setattr(qwen_run, "batch_size", lambda _loaded: 2)
    built = qwen.QwenEngine.__new__(qwen.QwenEngine)
    aligner = Aligner()
    built.asr, built.aligner = fake(heard), Loaded(aligner, aligner.processor)
    return built


def wav_file(tmp_path: Path, seconds: float) -> str:
    path = tmp_path / "sound.wav"
    rng = np.random.default_rng(1)
    soundfile.write(path, (rng.standard_normal(int(seconds * RATE)) * 0.1).astype(np.float32), RATE)
    return str(path)


def test_a_short_clip_comes_back_as_one_transcript_with_timed_words(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    found = engine(["language English<asr_text>Hello there, friend."], monkeypatch)
    heard = found.transcribe(wav_file(tmp_path, 4))
    assert heard.language == "English" and heard.text == "Hello there, friend."
    assert [(w.text, w.start, w.end) for w in heard.words] == [
        ("Hello", 0.0, 0.5), ("there,", 1.0, 1.5), ("friend.", 2.0, 2.5)]


def test_the_model_gets_the_prompt_qwen_asr_gave_it() -> None:
    assert qwen_run.PROMPT == ("<|im_start|>system\n<|im_end|>\n<|im_start|>user\n"
                               "<|audio_start|><|audio_pad|><|audio_end|><|im_end|>\n"
                               "<|im_start|>assistant\n")


def test_long_sound_is_heard_in_pieces_and_put_back_on_one_timeline(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    found = engine(["language English<asr_text>one", "language Arabic<asr_text>",
                    "language Arabic<asr_text>two three"], monkeypatch)
    heard = found.transcribe(wav_file(tmp_path, 400))
    assert heard.language == "English,Arabic" and heard.text == "one two three"
    starts = [w.start for w in heard.words]
    assert starts[0] == 0.0 and starts[1] > 350 and starts[2] == starts[1] + 1
    assert [len(call[0]) for call in found.asr.processor.calls] == [2, 1]  # two at a time
    assert len(found.aligner.processor.calls) == 1  # the silent piece is not aligned


def test_every_language_is_aligned_by_its_words_and_japanese_and_korean_by_their_own_split(
        monkeypatch: pytest.MonkeyPatch) -> None:
    aligner = Aligner()
    monkeypatch.setattr(qwen_run, "batch_size", lambda _loaded: 8)
    wav = np.zeros(RATE, dtype=np.float32)
    heard = [("Arabic", "مرحبا بكم"), ("Japanese", "こんにちは"), ("Korean", "안녕"), ("", "x")]
    stamps = qwen_run.align(Loaded(aligner, aligner.processor), [wav] * 4, heard)
    assert aligner.processor.split == [None, "Japanese", "Korean", None]
    assert stamps[0] == [Stamp("مرحبا", 0.0, 0.5), Stamp("بكم", 1.0, 1.5)]
    (texts, _), = aligner.processor.calls
    assert texts[0] == ("<|audio_start|><|audio_pad|><|audio_end|>مرحبا<timestamp><timestamp>"
                        "بكم<timestamp><timestamp>")


@pytest.mark.parametrize(("seconds", "count"), [(0.2, 1), (180, 1), (181, 2), (400, 3)])
def test_pieces_cover_the_whole_sound_and_each_is_cut_near_three_minutes(
        seconds: float, count: int) -> None:
    wav = np.random.default_rng(2).standard_normal(int(seconds * RATE)).astype(np.float32)
    parts = pieces.pieces(wav)
    assert len(parts) == count and parts[0].offset == 0.0
    assert all(len(p.wav) <= (pieces.LONGEST + pieces.SEARCH) * RATE for p in parts)
    if seconds >= pieces.SHORTEST:
        assert np.array_equal(np.concatenate([p.wav for p in parts]), wav)
    else:
        assert len(parts[0].wav) == pieces.SHORTEST * RATE


def test_a_piece_is_cut_at_the_quiet_moment_near_the_limit() -> None:
    wav = np.ones(int(200 * RATE), dtype=np.float32)
    wav[int(178 * RATE):int(178.3 * RATE)] = 0.0
    second = pieces.pieces(wav)[1]
    assert 178.0 <= second.offset <= 178.3


@pytest.mark.parametrize(("free", "device", "size"), [
    (16.0, "cuda", 8), (6.0, "cuda", 3), (1.5, "cuda", 1), (0.2, "cuda", 1), (8.0, "cpu", 2)])
def test_as_many_pieces_go_together_as_the_memory_left_holds(
        monkeypatch: pytest.MonkeyPatch, free: float, device: str, size: int) -> None:
    monkeypatch.setattr(qwen_run, "free_gb", lambda _device: free)
    model = types.SimpleNamespace(device=types.SimpleNamespace(type=device))
    assert qwen_run.batch_size(Loaded(model, None)) == size


@pytest.mark.parametrize(("raw", "expected"), [
    ("language English<asr_text>Hi.", ("English", "Hi.")),
    ("language ARABIC<asr_text> مرحبا ", ("Arabic", "مرحبا")),
    ("language None<asr_text>", ("", "")),
])
def test_the_language_is_written_as_qwen_asr_wrote_it(raw: str, expected: tuple[str, str]) -> None:
    class Parser:
        @staticmethod
        def parse_output(text: str) -> dict[str, Any]:
            language, _, said = text.partition("<asr_text>")
            name = language.removeprefix("language ")
            return {"language": None if name == "None" else name, "transcription": said}

    assert qwen_run.parsed(Parser(), raw) == expected
