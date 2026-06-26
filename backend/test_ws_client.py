"""
Smoke-test the backend WebSocket endpoint without any ESP32 hardware.

Usage:
    python test_ws_client.py [path/to/audio.wav]

If no WAV file is given, generates a 2-second silence buffer (useful for
testing the pipeline without a real recording).

Prints every state change and the final spoken response text.
"""
import asyncio
import json
import sys
import wave
import struct
import websockets


SERVER = "ws://localhost:7001/ws"
CHUNK = 2048  # bytes per audio frame sent to the server


async def run(pcm_bytes: bytes):
    async with websockets.connect(SERVER) as ws:
        print("[client] connected")

        msg = await ws.recv()
        print(f"[server] {msg}")

        await ws.send(json.dumps({"type": "button_pressed"}))
        print("[client] sent button_pressed")

        for i in range(0, len(pcm_bytes), CHUNK):
            await ws.send(pcm_bytes[i:i + CHUNK])

        await ws.send(json.dumps({"type": "audio_end"}))
        print(f"[client] sent {len(pcm_bytes)} bytes of audio + audio_end")

        while True:
            msg = await ws.recv()
            if isinstance(msg, bytes):
                print(f"[server] <audio chunk {len(msg)} bytes>")
            else:
                data = json.loads(msg)
                print(f"[server] {data}")
                if data.get("type") == "state" and data.get("value") == "idle":
                    break


def _load_wav(path: str) -> bytes:
    with wave.open(path, "rb") as wf:
        assert wf.getnchannels() == 1, "WAV must be mono"
        assert wf.getsampwidth() == 2, "WAV must be 16-bit"
        return wf.readframes(wf.getnframes())


def _silence(seconds: float = 2.0, rate: int = 16000) -> bytes:
    n = int(seconds * rate)
    return struct.pack(f"<{n}h", *([0] * n))


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pcm = _load_wav(sys.argv[1])
        print(f"[client] loaded {sys.argv[1]}, {len(pcm)} bytes")
    else:
        pcm = _silence()
        print("[client] using 2s silence buffer (no WAV file given)")

    asyncio.run(run(pcm))
