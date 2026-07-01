#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include "ws_client.h"
#include "config.h"

static WebSocketsClient _ws;
static StateCallback  _on_state;
static AudioCallback  _on_audio;
static TtsEndCallback _on_tts_end;
static bool _connected = false;

static void _event_handler(WStype_t type, uint8_t* payload, size_t len) {
    switch (type) {
        case WStype_CONNECTED:
            _connected = true;
            Serial.println("[WS] connected");
            break;

        case WStype_DISCONNECTED:
            _connected = false;
            Serial.println("[WS] disconnected");
            break;

        case WStype_TEXT: {
            JsonDocument doc;
            if (deserializeJson(doc, payload, len) != DeserializationError::Ok) break;
            const char* msg_type = doc["type"];
            if (!msg_type) break;

            if (strcmp(msg_type, "state") == 0) {
                const char* value = doc["value"];
                if (value && _on_state) _on_state(std::string(value));
            } else if (strcmp(msg_type, "tts_end") == 0) {
                if (_on_tts_end) _on_tts_end();
            } else if (strcmp(msg_type, "debug") == 0) {
                const char* transcript = doc["transcript"] | "";
                const char* response   = doc["response"] | "";
                const char* feeling    = doc["feeling"] | "";
                Serial.printf("[heard] %s\n", transcript);
                Serial.printf("[reply] %s (%s)\n", response, feeling);
            }
            break;
        }

        case WStype_BIN:
            if (_on_audio) _on_audio(payload, len);
            break;

        default:
            break;
    }
}

void ws_init(StateCallback on_state, AudioCallback on_audio, TtsEndCallback on_tts_end) {
    _on_state   = on_state;
    _on_audio   = on_audio;
    _on_tts_end = on_tts_end;
}

void ws_connect() {
    _ws.begin(SERVER_HOST, SERVER_PORT, SERVER_PATH);
    _ws.onEvent(_event_handler);
    _ws.setReconnectInterval(3000);
    Serial.printf("[WS] connecting to %s:%d%s\n", SERVER_HOST, SERVER_PORT, SERVER_PATH);
}

void ws_loop() {
    _ws.loop();
}

bool ws_is_connected() {
    return _connected;
}

void ws_send_json(const char* json) {
    _ws.sendTXT(json);
}

void ws_send_audio(const uint8_t* data, size_t len) {
    _ws.sendBIN(data, len);
}
