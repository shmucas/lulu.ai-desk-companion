/*
 * Lulu - XIAO ESP32-S3 firmware
 *
 * The mic streams continuously whenever the device is IDLE or RECORDING, so
 * the backend can hear the wake word ("Lulu") without a button press. The
 * button still works as a manual trigger and as "done talking".
 *
 * State machine:
 *   IDLE      -> button click, or server "listening" (wake word) -> RECORDING
 *   RECORDING -> button click (sends audio_end), or server "thinking"
 *                (silence endpoint) -> WAITING
 *   WAITING   -> server sends "speaking" -> PLAYING
 *   PLAYING   -> server sends tts_end -> IDLE (mic resumes)
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
        // Server-initiated (wake word) or echo of our button press. Either
        // way we are now capturing an utterance.
        if (g_state == State::IDLE) g_state = State::RECORDING;
        display_set_state(FaceState::LISTENING);
    } else if (value == "thinking") {
        // Server endpointed the utterance (silence) - stop streaming
        if (g_state == State::RECORDING) {
            audio_capture_stop();
            g_state = State::WAITING;
        }
        display_set_state(FaceState::THINKING);
    } else if (value == "speaking") {
        g_state = State::PLAYING;
        display_set_state(FaceState::SPEAKING);
        audio_playback_init();
    } else if (value == "idle") {
        if (g_state != State::RECORDING) {
            g_state = State::IDLE;
            display_set_state(FaceState::IDLE);
            // Keep the mic hot for the wake word
            if (!audio_is_capturing()) audio_capture_start();
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
        if (!audio_is_capturing()) audio_capture_start();
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
    // Stream while RECORDING (command) and while IDLE (wake word listening)
    if (g_state != State::RECORDING && g_state != State::IDLE) return;
    if (!ws_is_connected() || !audio_is_capturing()) return;
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
    audio_capture_start();   // mic always hot while idle - feeds wake word

    ws_init(on_state, on_audio, on_tts_end);
    ws_connect();

    display_set_state(FaceState::IDLE);
    Serial.println("[main] ready");
}

void loop() {
    ws_loop();

    handle_button();
    stream_audio();
    display_tick();

    // Auto-recover from error state after 2 seconds
    if (g_state == State::ERROR_STATE && millis() - g_error_ts > 2000) {
        g_state = State::IDLE;
        display_set_state(FaceState::IDLE);
        if (!audio_is_capturing()) audio_capture_start();
    }

    delay(5);
}
