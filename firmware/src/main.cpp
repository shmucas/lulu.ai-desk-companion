/*
 * Lulu - XIAO ESP32-S3 firmware
 *
 * State machine:
 *   IDLE      → button press → RECORDING
 *   RECORDING → button release → WAITING  (streams audio to Mac)
 *   WAITING   → server sends "speaking" → PLAYING
 *   PLAYING   → server sends tts_end → IDLE
 *   any state → server sends "error" → ERROR → IDLE (after 2s)
 */
#include <Arduino.h>
#include "config.h"
#include "wifi_manager.h"
#include "ws_client.h"
#include "audio.h"
#include "display.h"

enum class State { IDLE, RECORDING, WAITING, PLAYING, ERROR_STATE };

static State g_state = State::IDLE;
static bool  g_button_last = HIGH;
static unsigned long g_error_ts = 0;

// ── WebSocket callbacks ──────────────────────────────────────────────────────

void on_state(const std::string& value) {
    Serial.printf("[main] server state: %s\n", value.c_str());
    if (value == "listening") {
        display_set_state(FaceState::LISTENING);
    } else if (value == "thinking") {
        display_set_state(FaceState::THINKING);
    } else if (value == "speaking") {
        g_state = State::PLAYING;
        display_set_state(FaceState::SPEAKING);
        audio_playback_init();
    } else if (value == "idle") {
        if (g_state != State::RECORDING) {
            g_state = State::IDLE;
            display_set_state(FaceState::IDLE);
        }
    } else if (value == "error") {
        g_state = State::ERROR_STATE;
        g_error_ts = millis();
        display_set_state(FaceState::ERROR_STATE);
    }
}

void on_audio(const uint8_t* data, size_t len) {
    if (g_state == State::PLAYING) {
        audio_play_chunk(data, len);
    }
}

void on_tts_end() {
    Serial.println("[main] TTS stream complete");
    audio_playback_stop();
    g_state = State::IDLE;
    display_set_state(FaceState::IDLE);
}

// ── Button handling ──────────────────────────────────────────────────────────

void handle_button() {
    bool pressed = (digitalRead(BUTTON_PIN) == LOW);
    bool was_pressed = (g_button_last == LOW);

    // Debounce: only act on edges
    if (pressed == was_pressed) return;
    g_button_last = pressed ? LOW : HIGH;

    if (pressed && g_state == State::IDLE && ws_is_connected()) {
        Serial.println("[main] button pressed - start recording");
        g_state = State::RECORDING;
        audio_capture_start();
        ws_send_json("{\"type\":\"button_pressed\"}");
    }

    if (!pressed && g_state == State::RECORDING) {
        Serial.println("[main] button released - end recording");
        audio_capture_stop();
        g_state = State::WAITING;
        ws_send_json("{\"type\":\"audio_end\"}");
    }
}

// ── Audio streaming loop ─────────────────────────────────────────────────────

static uint8_t _audio_buf[AUDIO_CHUNK_BYTES];

void stream_audio() {
    if (g_state != State::RECORDING) return;
    size_t n = audio_read_chunk(_audio_buf, AUDIO_CHUNK_BYTES);
    if (n > 0) {
        ws_send_audio(_audio_buf, n);
    }
}

// ── Setup & loop ─────────────────────────────────────────────────────────────

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("[main] Lulu booting...");

    display_init();
    display_set_state(FaceState::STANDBY);

    pinMode(BUTTON_PIN, INPUT_PULLUP);
    g_button_last = HIGH;

    wifi_init();

    audio_init();

    ws_init(on_state, on_audio, on_tts_end);
    ws_connect();

    display_set_state(FaceState::IDLE);
    Serial.println("[main] ready");
}

void loop() {
    ws_loop();

    handle_button();
    stream_audio();

    // Auto-recover from error state after 2 seconds
    if (g_state == State::ERROR_STATE && millis() - g_error_ts > 2000) {
        g_state = State::IDLE;
        display_set_state(FaceState::IDLE);
    }

    delay(5);
}
