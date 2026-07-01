#!/usr/bin/env bash
# Start the Lulu backend with the correct Piper binary and voice model.
# The venv's piper avoids the broken system binary in /usr/local/bin.
set -e
cd "$(dirname "$0")"

export PIPER_BINARY="$PWD/.venv/bin/piper"
export PIPER_MODEL="$PWD/en_US-lessac-medium.onnx"

# Play Lulu's voice on the Mac (default output device, incl. a Bluetooth
# speaker). Comment this out to use the ESP32's onboard speaker instead.
export PLAYBACK=mac

exec .venv/bin/uvicorn main:app --reload --host 0.0.0.0 --port 7001
