import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
AGENT_MODEL = os.getenv("AGENT_MODEL", "qwen3:1.7b")
CONV_MODEL = os.getenv("CONV_MODEL", "gemma3:1b")
MAX_TOOL_ITERATIONS = 5

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base.en")
PIPER_BINARY = os.getenv("PIPER_BINARY", "piper")
PIPER_MODEL = os.getenv("PIPER_MODEL", "en_US-lessac-medium.onnx")

AUDIO_SAMPLE_RATE = 16000
TTS_SAMPLE_RATE = 22050

# Where Lulu's voice comes out:
#   "esp32" - stream TTS audio to the device speaker (MAX98357A)
#   "mac"   - play TTS on the Mac's default output device (also covers a
#             Bluetooth speaker: just connect it and set it as Mac output)
PLAYBACK = os.getenv("PLAYBACK", "esp32")

# Wake word ("Lulu") - EXPERIMENTAL, off by default. Continuous idle
# streaming overwhelmed the device (backend wake checks stall the socket,
# backpressure piles up on the ESP32). Firmware also no longer streams while
# idle, so enabling this needs a firmware change too. Button-only for now.
WAKE_ENABLED = os.getenv("WAKE_ENABLED", "0") == "1"

# RMS energy (int16 scale) above which a chunk counts as speech. Raise if
# background noise triggers wake checks constantly; lower if Lulu misses you.
WAKE_RMS = int(os.getenv("WAKE_RMS", "500"))

# Where Lulu's ears are:
#   "esp32" - use the I2S mic (INMP441) streamed from the device
#   "mac"   - capture from the Mac's own microphone instead, while the
#             device's mic wiring is being debugged. Button on the ESP32
#             still drives listening/thinking state as normal.
AUDIO_INPUT = os.getenv("AUDIO_INPUT", "esp32")
