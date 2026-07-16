"""
Test the full pipeline using the Mac's built-in microphone instead of the
ESP32, while the device's I2S mic wiring is being debugged.

Usage:
    python mic_test_client.py [seconds]

Records from the Mac mic (avfoundation device "MacBook Pro Microphone"),
converts to 16-bit mono 16kHz PCM, and sends it to the backend exactly like
test_ws_client.py does.
"""
import asyncio
import json
import subprocess
import sys
import tempfile
import wave

from test_ws_client import run as ws_run

MAC_MIC_DEVICE = "1"  # ffmpeg -f avfoundation -list_devices true -i ""


def record(seconds: float) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    print(f"[mic] recording {seconds:.1f}s from MacBook Pro Microphone...")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "avfoundation", "-i", f":{MAC_MIC_DEVICE}",
            "-t", str(seconds),
            "-ar", "16000", "-ac", "1", "-sample_fmt", "s16",
            tmp_path,
        ],
        check=True,
        capture_output=True,
    )
    print("[mic] recording done")

    with wave.open(tmp_path, "rb") as wf:
        return wf.readframes(wf.getnframes())


if __name__ == "__main__":
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
    pcm = record(seconds)
    print(f"[mic] {len(pcm)} bytes captured")
    asyncio.run(ws_run(pcm))
