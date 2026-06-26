#pragma once

// ── WiFi ────────────────────────────────────────────────────────────────────
#define WIFI_SSID     "YOUR_SSID"
#define WIFI_PASSWORD "YOUR_PASSWORD"

// ── Backend server ───────────────────────────────────────────────────────────
// Use the Mac's local IP address. mDNS is unreliable on ESP32.
// Find your Mac's IP: System Settings → WiFi → Details
#define SERVER_HOST "192.168.1.X"
#define SERVER_PORT 7001
#define SERVER_PATH "/ws"

// ── I2S Microphone (INMP441) — XIAO ESP32-S3 pins ───────────────────────────
#define MIC_BCK_PIN  7    // D8
#define MIC_WS_PIN   8    // D9
#define MIC_DATA_PIN 9    // D10

// ── I2S Amplifier (MAX98357A) ────────────────────────────────────────────────
#define AMP_BCK_PIN  2    // D1
#define AMP_WS_PIN   3    // D2
#define AMP_DATA_PIN 4    // D3

// ── OLED SSD1306 (I2C) ──────────────────────────────────────────────────────
#define OLED_SDA_PIN 5    // D4
#define OLED_SCL_PIN 6    // D5
#define OLED_WIDTH   128
#define OLED_HEIGHT  64
#define OLED_ADDR    0x3C

// ── Button (push-to-talk) ────────────────────────────────────────────────────
#define BUTTON_PIN   1    // D0 — active LOW (press = GND)

// ── Audio ────────────────────────────────────────────────────────────────────
#define AUDIO_SAMPLE_RATE   16000
#define AUDIO_BITS          16
#define AUDIO_CHANNELS      1
#define AUDIO_CHUNK_SAMPLES 512           // frames per I2S read
#define AUDIO_CHUNK_BYTES   (AUDIO_CHUNK_SAMPLES * 2)

#define TTS_SAMPLE_RATE     22050
