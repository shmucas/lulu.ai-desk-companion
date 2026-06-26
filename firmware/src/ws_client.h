#pragma once
#include <functional>
#include <string>

using StateCallback = std::function<void(const std::string& state)>;
using AudioCallback = std::function<void(const uint8_t* data, size_t len)>;
using TtsEndCallback = std::function<void()>;

void ws_init(StateCallback on_state, AudioCallback on_audio, TtsEndCallback on_tts_end);
void ws_connect();
void ws_loop();
bool ws_is_connected();
void ws_send_json(const char* json);
void ws_send_audio(const uint8_t* data, size_t len);
