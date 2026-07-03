#pragma once
#include <stddef.h>
#include <stdint.h>

void audio_init();
void audio_capture_start();
void audio_capture_stop();
bool audio_is_capturing();      // true while the mic is running
size_t audio_read_chunk(uint8_t* buf, size_t len);
int16_t audio_capture_peak();   // loudest sample since capture start (0..32767)

void audio_playback_init();
void audio_play_chunk(const uint8_t* buf, size_t len);
void audio_playback_stop();
