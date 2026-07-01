/*
 * Lulu - XIAO ESP32-S3 firmware
 *
 * State machine (click-to-toggle button):
 *   IDLE      -> button click -> RECORDING  (streams audio to Mac)
 *   RECORDING -> button click -> WAITING    (sends audio_end, "done talking")
 *   WAITING   -> server sends "speaking" -> PLAYING
 *   PLAYING   -> server sends tts_end -> IDLE
 *   any state -> server sends "error" -> ERROR -> IDLE (after 2s)
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
static unsigned long g_button_edge_ts = 0;

// Ignore button edges that arrive within this window of the last accepted
// click, so mechanical contact bounce cannot toggle recording twice.
static const unsigned long BUTTON_DEBOUNCE_MS = 250;

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

    // Only act on state changes (edges)
    if (pressed == was_pressed) return;
    g_button_last = pressed ? LOW : HIGH;

    // Click-to-toggle: only the press edge matters, ignore the release
    if (!pressed) return;

    // Debounce: drop press edges that come too soon after the last click
    unsigned long now = millis();
    if (now - g_button_edge_ts < BUTTON_DEBOUNCE_MS) return;
    g_button_edge_ts = now;

    if (g_state == State::IDLE && ws_is_connected()) {
        Serial.println("[main] button click - start listening");
        g_state = State::RECORDING;
        audio_capture_start();
        ws_send_json("{\"type\":\"button_pressed\"}");
    } else if (g_state == State::RECORDING) {
        Serial.printf("[main] button click - done talking (mic peak %d/32767), thinking\n",
                      audio_capture_peak());
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
