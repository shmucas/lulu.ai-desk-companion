import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
AGENT_MODEL = os.getenv("AGENT_MODEL", "qwen3:1.7b")
CONV_MODEL = os.getenv("CONV_MODEL", "gemma3:1b")
MAX_TOOL_ITERATIONS = 5
