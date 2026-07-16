"""
Per-connection WebSocket session.

The device streams mic audio continuously while idle. The session runs one
of three modes:

  wake    - watch the stream for the wake word ("Lulu"). Chunks land in a
            rolling ring buffer; when recent audio has speech energy, the
            last ~2.5s are transcribed and checked for the name. A button
            press skips straight to command mode.
  command - accumulate an utterance. Ends on ~1.3s of trailing silence, a
            12s cap, or an explicit audio_end (button click).
  busy    - STT + LLM + TTS in flight; incoming audio is ignored.

Audio arrives as binary WebSocket frames (PCM 16-bit mono 16kHz).
TTS audio is sent back as binary frames (PCM 16-bit mono 22050Hz).
State changes are broadcast as JSON: {"type": "state", "value": "<state>"}

Timers/reminders call announce() (via timekeeper) to speak spontaneously.
"""
import asyncio
import json
import re
import time
import traceback

import numpy as np
import sounddevice as sd
from fastapi import WebSocket

import stt
import tts
import llm
from config import AUDIO_INPUT, PLAYBACK, WAKE_ENABLED, WAKE_RMS

_TTS_CHUNK_SIZE = 4096
_BYTES_PER_SEC = 16000 * 2  # 16kHz, 16-bit mono

# Wake mode tuning
_RING_BYTES = int(3.0 * _BYTES_PER_SEC)         # rolling context kept for detection
_DETECT_BYTES = int(2.5 * _BYTES_PER_SEC)       # window transcribed per check
_MIN_DETECT_BYTES = int(1.2 * _BYTES_PER_SEC)   # don't bother below this
_DETECT_INTERVAL_S = 0.7                        # min gap between whisper checks
_VOICE_RECENT_S = 0.6                           # speech energy must be this fresh
_COOLDOWN_S = 1.0                               # deaf period after Lulu speaks

# Command mode tuning
_ENDPOINT_SILENCE_S = 1.3                       # trailing silence that ends an utterance
_MAX_UTTERANCE_S = 12.0
_NO_SPEECH_TIMEOUT_S = 6.0                      # wake fired but nobody said anything

_WAKE_VARIANTS = ("lulu", "loulou", "lulou", "loulu", "looloo")


def _log(msg: str):
    print(f"[session] {msg}", flush=True)


def _rms(chunk: bytes) -> float:
    samples = np.frombuffer(chunk, dtype=np.int16)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples.astype(np.float32) ** 2)))


def _wake_match(text: str) -> bool:
    normalized = re.sub(r"[^a-z]", "", text.lower())
    return any(v in normalized for v in _WAKE_VARIANTS)


class WSSession:
    def __init__(self, ws: WebSocket):
        self._ws = ws
        self._history: list[dict] = []
        self._mode = "wake"
        self._speak_lock = asyncio.Lock()

        # wake mode state
        self._ring = bytearray()
        self._last_voice_ts = 0.0
        self._last_detect_ts = 0.0
        self._cooldown_until = 0.0

        # command mode state
        self._cmd_buf = bytearray()
        self._cmd_start_ts = 0.0
        self._cmd_heard_speech = False
        self._cmd_last_voice_ts = 0.0

        # mac mic capture (AUDIO_INPUT == "mac")
        self._mac_stream = None

    async def handle(self):
        await self._send_state("idle")
        if WAKE_ENABLED:
            _log('wake word active - say "Lulu" or press the button')
        try:
            while True:
                msg = await self._ws.receive()
                if msg.get("bytes"):
                    await self._on_audio(msg["bytes"])
                elif msg.get("text"):
                    await self._handle_json(json.loads(msg["text"]))
        except Exception:
            _log("connection closed")

    # ── incoming audio ───────────────────────────────────────────────────────

    async def _on_audio(self, chunk: bytes):
        if AUDIO_INPUT == "mac":
            return  # audio comes from the Mac mic instead, see _start_mac_recording
        if self._mode == "command":
            await self._command_audio(chunk)
        elif self._mode == "wake":
            await self._wake_audio(chunk)
        # busy: drop

    async def _wake_audio(self, chunk: bytes):
        if not WAKE_ENABLED:
            return
        now = time.monotonic()
        if now < self._cooldown_until:
            return

        self._ring.extend(chunk)
        if len(self._ring) > _RING_BYTES:
            del self._ring[:len(self._ring) - _RING_BYTES]

        if _rms(chunk) >= WAKE_RMS:
            self._last_voice_ts = now

        if (now - self._last_detect_ts < _DETECT_INTERVAL_S
                or now - self._last_voice_ts > _VOICE_RECENT_S
                or len(self._ring) < _MIN_DETECT_BYTES):
            return

        self._last_detect_ts = now
        snippet = bytes(self._ring[-_DETECT_BYTES:])
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, stt.transcribe, snippet)
        # Mode may have flipped while transcribing (button press)
        if text and self._mode == "wake" and _wake_match(text):
            _log(f"wake word heard in {text!r}")
            await self._begin_command()

    async def _command_audio(self, chunk: bytes):
        self._cmd_buf.extend(chunk)
        now = time.monotonic()
        if _rms(chunk) >= WAKE_RMS:
            self._cmd_heard_speech = True
            self._cmd_last_voice_ts = now

        elapsed = now - self._cmd_start_ts
        if not self._cmd_heard_speech:
            if elapsed >= _NO_SPEECH_TIMEOUT_S:
                _log("no speech after wake, back to idle")
                await self._reset_to_wake()
            return

        if now - self._cmd_last_voice_ts >= _ENDPOINT_SILENCE_S:
            _log(f"silence endpoint after {elapsed:.1f}s")
            await self._process(bytes(self._cmd_buf))
        elif elapsed >= _MAX_UTTERANCE_S:
            _log("max utterance length reached")
            await self._process(bytes(self._cmd_buf))

    # ── control messages ─────────────────────────────────────────────────────

    async def _handle_json(self, data: dict):
        msg_type = data.get("type")
        if msg_type == "button_pressed":
            _log("button pressed - listening")
            await self._begin_command()
        elif msg_type == "audio_end":
            if self._mode == "command":
                if AUDIO_INPUT == "mac":
                    self._stop_mac_recording()
                await self._process(bytes(self._cmd_buf))

    async def _begin_command(self):
        self._mode = "command"
        self._cmd_buf.clear()
        self._ring.clear()
        now = time.monotonic()
        self._cmd_start_ts = now
        self._cmd_heard_speech = False
        self._cmd_last_voice_ts = now
        if AUDIO_INPUT == "mac":
            self._start_mac_recording()
        await self._send_state("listening")

    def _start_mac_recording(self):
        _log("recording from Mac mic")
        self._cmd_buf.clear()

        def callback(indata, frames, time_info, status):
            self._cmd_buf.extend(bytes(indata))

        self._mac_stream = sd.RawInputStream(
            samplerate=16000, channels=1, dtype="int16", callback=callback
        )
        self._mac_stream.start()

    def _stop_mac_recording(self):
        if self._mac_stream:
            self._mac_stream.stop()
            self._mac_stream.close()
            self._mac_stream = None

    async def _reset_to_wake(self):
        self._mode = "wake"
        self._ring.clear()
        self._cmd_buf.clear()
        self._last_voice_ts = 0.0
        self._cooldown_until = time.monotonic() + _COOLDOWN_S
        await self._send_state("idle")

    # ── pipeline ─────────────────────────────────────────────────────────────

    async def _process(self, pcm: bytes):
        self._mode = "busy"

        samples = np.frombuffer(pcm, dtype=np.int16) if pcm else np.zeros(1, dtype=np.int16)
        _log(f"utterance ended - {len(pcm)} bytes (~{len(pcm) / _BYTES_PER_SEC:.1f}s), "
             f"rms {_rms(pcm):.0f}, peak {int(np.abs(samples).max())}/32767")
        if len(pcm) < 3200:
            _log("audio too short, ignoring")
            await self._reset_to_wake()
            return

        try:
            await self._send_state("thinking")

            loop = asyncio.get_event_loop()

            t0 = time.perf_counter()
            transcript = await loop.run_in_executor(None, stt.transcribe, pcm)
            _log(f"STT ({time.perf_counter() - t0:.1f}s) heard: {transcript!r}")
            if not transcript:
                _log("empty transcript - no speech detected in the audio")
                await self._reset_to_wake()
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

            async with self._speak_lock:
                await self._speak(response.message)
            await self._reset_to_wake()

        except Exception:
            _log("pipeline error:\n" + traceback.format_exc())
            await self._send_state("error")
            await asyncio.sleep(2)
            await self._reset_to_wake()

    async def _speak(self, text: str):
        """Send the speaking state, play/stream TTS, then close with tts_end."""
        await self._send_state("speaking")
        loop = asyncio.get_event_loop()
        t0 = time.perf_counter()
        if PLAYBACK == "mac":
            await loop.run_in_executor(None, tts.speak_on_mac, text)
            _log(f"TTS+playback on Mac ({time.perf_counter() - t0:.1f}s)")
        else:
            audio_bytes = await loop.run_in_executor(None, tts.synthesize, text)
            _log(f"TTS ({time.perf_counter() - t0:.1f}s) produced {len(audio_bytes)} PCM bytes")
            await self._stream_audio(audio_bytes)

        # Always send tts_end: on "speaking" the device switches I2S to
        # playback, and tts_end is what restores mic capture mode. Skipping
        # it (even in Mac-playback mode) leaves the mic dead after one reply.
        await self._send_json({"type": "tts_end"})

    async def announce(self, text: str):
        """Speak spontaneously (timers, reminders). Called by timekeeper."""
        _log(f"announce: {text!r}")
        self._mode = "busy"
        try:
            await self._send_json({
                "type": "debug",
                "transcript": "",
                "response": text,
                "feeling": "neutral",
            })
            async with self._speak_lock:
                await self._speak(text)
            self._history.append({"role": "assistant", "content": text})
        finally:
            await self._reset_to_wake()

    # ── plumbing ─────────────────────────────────────────────────────────────

    async def _stream_audio(self, pcm: bytes):
        for i in range(0, len(pcm), _TTS_CHUNK_SIZE):
            await self._ws.send_bytes(pcm[i:i + _TTS_CHUNK_SIZE])
            await asyncio.sleep(0)

    async def _send_state(self, value: str):
        await self._send_json({"type": "state", "value": value})

    async def _send_json(self, data: dict):
        await self._ws.send_text(json.dumps(data))
