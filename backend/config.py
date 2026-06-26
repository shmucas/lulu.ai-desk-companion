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
