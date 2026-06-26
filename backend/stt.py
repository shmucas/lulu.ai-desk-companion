"""
Speech-to-text via faster-whisper.
Accepts raw PCM bytes (16-bit signed, mono) and returns a transcript string.
"""
import io
import numpy as np
import soundfile as sf
from faster_whisper import WhisperModel
from config import WHISPER_MODEL, AUDIO_SAMPLE_RATE

_model: WhisperModel | None = None


def load():
    global _model
    _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")


def transcribe(pcm_bytes: bytes, sample_rate: int = AUDIO_SAMPLE_RATE) -> str:
    if _model is None:
        raise RuntimeError("STT model not loaded - call stt.load() first")

    audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    buf = io.BytesIO()
    sf.write(buf, audio, sample_rate, format="WAV", subtype="FLOAT")
    buf.seek(0)

    segments, _ = _model.transcribe(buf, language="en", beam_size=1, vad_filter=True)
    return " ".join(seg.text.strip() for seg in segments).strip()
