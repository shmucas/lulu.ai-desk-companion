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
from fastapi import WebSocket

import stt
import tts
import llm

_TTS_CHUNK_SIZE = 4096


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
            pass

    async def _handle_json(self, data: dict):
        msg_type = data.get("type")
        if msg_type == "button_pressed":
            self._audio_buf.clear()
            await self._send_state("listening")
        elif msg_type == "audio_end":
            await self._process()

    async def _process(self):
        pcm = bytes(self._audio_buf)
        self._audio_buf.clear()

        if len(pcm) < 3200:
            await self._send_state("idle")
            return

        try:
            await self._send_state("thinking")

            loop = asyncio.get_event_loop()
            transcript = await loop.run_in_executor(None, stt.transcribe, pcm)
            if not transcript:
                await self._send_state("idle")
                return

            self._history.append({"role": "user", "content": transcript})
            response = await llm.run_pipeline(transcript, self._history[:-1])
            self._history.append({"role": "assistant", "content": response.message})

            if len(self._history) > 20:
                self._history = self._history[-20:]

            await self._send_state("speaking")
            audio_bytes = await loop.run_in_executor(None, tts.synthesize, response.message)
            await self._stream_audio(audio_bytes)
            await self._send_json({"type": "tts_end"})
            await self._send_state("idle")

        except Exception:
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
