# Lulu Desk Companion

An AI desk companion built on a Seeed XIAO ESP32-S3. The device handles all hardware I/O (microphone, speaker, OLED display, button). The Mac acts as the AI brain over local WiFi.

Press the button and talk. Lulu answers out loud with an animated pixel face: she blinks, glances around, and moves her mouth while speaking.

## Features

- Weather, web search, current time, jokes
- Timers and reminders, announced out loud when they fire
- Persistent memory: "remember that my dog is named Biscuit"
- Animated OLED face with six states and idle animations

## Hardware

| Part | Notes |
|---|---|
| Seeed XIAO ESP32-S3 | With PSRAM enabled |
| SSD1306 128x64 OLED | I2C at 0x3C |
| INMP441 I2S MEMS mic | Connected to D8/D9/D10 |
| MAX98357A I2S amp | Connected to D1/D2/D3 |
| 4 ohm 3W speaker | Wired to MAX98357A outputs |
| Tactile button | Push-to-talk on D0, active LOW |

Full pin-by-pin wiring: [docs/WIRING.md](docs/WIRING.md)

## Starting the Backend

Open a terminal and run:

```bash
cd backend
./run.sh
```

That's it. The script activates the virtual environment and starts the server on port 7001.

First time setup only - create the virtual environment and install dependencies:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Firmware Setup

1. Edit `firmware/src/config.h` and set your WiFi credentials and Mac's local IP:

```c
#define WIFI_SSID     "your_network"
#define WIFI_PASSWORD "your_password"
#define SERVER_HOST   "192.168.x.x"
```

Find your Mac's IP at System Settings - WiFi - Details - IP Address.

2. Flash the firmware:

```bash
cd firmware
pio run --target upload
```

3. Monitor serial output (optional):

```bash
pio device monitor
```

## Architecture

```
XIAO ESP32-S3 (hardware)         Mac (AI backend)
--------------------------        --------------------------------
WiFi + WebSocket client  <------> FastAPI WebSocket server
INMP441 I2S mic          audio    faster-whisper STT
MAX98357A I2S amp        stream   Ollama Qwen3 1.7B (agentic)
SSD1306 128x64 OLED      state    Ollama Gemma3 1B (conversational)
Push-to-talk button      msgs     Piper TTS
```

## Running

1. Start the backend on your Mac: `cd backend && ./run.sh`
2. Power the ESP32 via USB-C - it connects automatically over WiFi
3. Press the button and speak

Speak your request after the click; Lulu detects when you stop talking
(~1.3s of silence). Clicking the button again also force-ends the utterance.

Useful backend env vars:

| Var | Default | Meaning |
|---|---|---|
| `PLAYBACK` | `esp32` | `mac` plays TTS on the Mac / Bluetooth speaker |
| `WAKE_ENABLED` | `0` | Experimental wake word backend, off by default (needs firmware-side idle streaming too, currently disabled) |
| `WAKE_RMS` | `500` | Speech energy threshold for the experimental wake path |
