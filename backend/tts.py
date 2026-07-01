"""
Text-to-speech via Piper.
Returns raw PCM bytes (16-bit signed, mono, TTS_SAMPLE_RATE Hz).
"""
import subprocess
import tempfile
import os
from config import PIPER_BINARY, PIPER_MODEL


def synthesize(text: str) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        subprocess.run(
            [PIPER_BINARY, "--model", PIPER_MODEL, "--output_file", tmp_path],
            input=text.encode(),
            check=True,
            capture_output=True,
        )
        with open(tmp_path, "rb") as f:
            wav_data = f.read()
        return _strip_wav_header(wav_data)
    finally:
        os.unlink(tmp_path)


def _strip_wav_header(wav_bytes: bytes) -> bytes:
    """Remove 44-byte WAV header to return raw PCM."""
    return wav_bytes[44:]


def speak_on_mac(text: str) -> None:
    """Synthesize `text` and play it on the Mac's default output device via
    afplay. Follows the current output device, so a connected Bluetooth
    speaker works with no code change. Blocking - call in an executor."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        subprocess.run(
            [PIPER_BINARY, "--model", PIPER_MODEL, "--output_file", tmp_path],
            input=text.encode(),
            check=True,
            capture_output=True,
        )
        subprocess.run(["afplay", tmp_path], check=True)
    finally:
        os.unlink(tmp_path)
