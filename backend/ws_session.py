"""
Per-connection WebSocket session.

Manages the state machine for one ESP32 connection:
  IDLE → LISTENING → THINKING → SPEAKING → IDLE

Audio arrives as binary WebSocket frames (PCM 16-bit mono 16kHz).
TTS audio is sent back as binary frames (PCM 16-bit mono 22050Hz).
State changes are broadcast as JSON: {"type": "state", "value": "<state>"}
"""
import asyncio
import json
import time
import traceback
from fastapi import WebSocket

import stt
import tts
import llm
from config import PLAYBACK

_TTS_CHUNK_SIZE = 4096


def _log(msg: str):
    print(f"[session] {msg}", flush=True)


class WSSession:
    def __init__(self, ws: WebSocket):
        self._ws = ws
        self._audio_buf = bytearray()
        self._history: list[dict] = []

    async def handle(self):
        await self._send_state("idle")
        try:
            while True:
                msg = await self._ws.receive()
                if "bytes" in msg:
                    self._audio_buf.extend(msg["bytes"])
                elif "text" in msg:
                    await self._handle_json(json.loads(msg["text"]))
        except Exception:
            _log("connection closed")

    async def _handle_json(self, data: dict):
        msg_type = data.get("type")
        if msg_type == "button_pressed":
            self._audio_buf.clear()
            _log("button pressed - listening")
            await self._send_state("listening")
        elif msg_type == "audio_end":
            await self._process()

    async def _process(self):
        pcm = bytes(self._audio_buf)
        self._audio_buf.clear()

        _log(f"audio_end - received {len(pcm)} bytes (~{len(pcm) / 32000:.1f}s)")
        if len(pcm) < 3200:
            _log("audio too short, ignoring")
            await self._send_state("idle")
            return

        try:
            await self._send_state("thinking")

            loop = asyncio.get_event_loop()

            t0 = time.perf_counter()
            transcript = await loop.run_in_executor(None, stt.transcribe, pcm)
            _log(f"STT ({time.perf_counter() - t0:.1f}s) heard: {transcript!r}")
            if not transcript:
                _log("empty transcript, back to idle")
                await self._send_state("idle")
                return

            self._history.append({"role": "user", "content": transcript})
            t0 = time.perf_counter()
            response = await llm.run_pipeline(transcript, self._history[:-1])
            _log(f"LLM ({time.perf_counter() - t0:.1f}s) reply: {response.message!r} "
                 f"[feeling={response.feeling}]")
            self._history.append({"role": "assistant", "content": response.message})

            if len(self._history) > 20:
                self._history = self._history[-20:]

            # Mirror transcript + reply to the ESP32 so they show in pio monitor
            await self._send_json({
                "type": "debug",
                "transcript": transcript,
                "response": response.message,
                "feeling": response.feeling,
            })

            await self._send_state("speaking")
            t0 = time.perf_counter()
            if PLAYBACK == "mac":
                await loop.run_in_executor(None, tts.speak_on_mac, response.message)
                _log(f"TTS+playback on Mac ({time.perf_counter() - t0:.1f}s)")
            else:
                audio_bytes = await loop.run_in_executor(None, tts.synthesize, response.message)
                _log(f"TTS ({time.perf_counter() - t0:.1f}s) produced {len(audio_bytes)} PCM bytes")
                await self._stream_audio(audio_bytes)

            # Always send tts_end: on "speaking" the device switches I2S to
            # playback, and tts_end is what restores mic capture mode. Skipping
            # it (even in Mac-playback mode) leaves the mic dead after one reply.
            await self._send_json({"type": "tts_end"})
            await self._send_state("idle")

        except Exception:
            _log("pipeline error:\n" + traceback.format_exc())
            await self._send_state("error")
            await asyncio.sleep(2)
            await self._send_state("idle")

    async def _stream_audio(self, pcm: bytes):
        for i in range(0, len(pcm), _TTS_CHUNK_SIZE):
            await self._ws.send_bytes(pcm[i:i + _TTS_CHUNK_SIZE])
            await asyncio.sleep(0)

    async def _send_state(self, value: str):
        await self._send_json({"type": "state", "value": value})

    async def _send_json(self, data: dict):
        await self._ws.send_text(json.dumps(data))
