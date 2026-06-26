#pragma once
#include <stddef.h>
#include <stdint.h>

void audio_init();
void audio_capture_start();
void audio_capture_stop();
size_t audio_read_chunk(uint8_t* buf, size_t len);

void audio_playback_init();
void audio_play_chunk(const uint8_t* buf, size_t len);
void audio_playback_stop();
