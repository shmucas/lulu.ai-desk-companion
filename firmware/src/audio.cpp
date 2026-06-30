/*
 * I2S audio - capture (INMP441) and playback (MAX98357A).
 *
 * XIAO ESP32-S3 has one I2S peripheral that can be reconfigured.
 * We use a single I2S instance, swapping config between capture and playback.
 *
 * Capture:  16kHz, 16-bit, mono  (INMP441 outputs mono on SD pin)
 * Playback: 22050Hz, 16-bit, stereo (MAX98357A expects stereo frames; mono
 *           PCM is duplicated on both channels via channel_format)
 */
#include <Arduino.h>
#include <driver/i2s.h>
#include "audio.h"
#include "config.h"

#define I2S_PORT I2S_NUM_0

static void _install_capture() {
    i2s_config_t cfg = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = AUDIO_SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 4,
        .dma_buf_len = AUDIO_CHUNK_SAMPLES,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0,
    };
    i2s_pin_config_t pins = {
        .bck_io_num = MIC_BCK_PIN,
        .ws_io_num = MIC_WS_PIN,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = MIC_DATA_PIN,
    };
    i2s_driver_install(I2S_PORT, &cfg, 0, nullptr);
    i2s_set_pin(I2S_PORT, &pins);
}

static void _install_playback() {
    i2s_config_t cfg = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate = TTS_SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,  // duplicate mono → stereo
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 512,
        .use_apll = false,
        .tx_desc_auto_clear = true,
        .fixed_mclk = 0,
    };
    i2s_pin_config_t pins = {
        .bck_io_num = AMP_BCK_PIN,
        .ws_io_num = AMP_WS_PIN,
        .data_out_num = AMP_DATA_PIN,
        .data_in_num = I2S_PIN_NO_CHANGE,
    };
    i2s_driver_install(I2S_PORT, &cfg, 0, nullptr);
    i2s_set_pin(I2S_PORT, &pins);
}

void audio_init() {
    _install_capture();
    Serial.println("[audio] mic ready (16kHz 16-bit mono)");
}

void audio_capture_start() {
    i2s_start(I2S_PORT);
}

void audio_capture_stop() {
    i2s_stop(I2S_PORT);
}

size_t audio_read_chunk(uint8_t* buf, size_t len) {
    size_t bytes_read = 0;
    i2s_read(I2S_PORT, buf, len, &bytes_read, portMAX_DELAY);
    return bytes_read;
}

void audio_playback_init() {
    i2s_driver_uninstall(I2S_PORT);
    _install_playback();
    Serial.println("[audio] speaker ready (22050Hz stereo)");
}

void audio_play_chunk(const uint8_t* buf, size_t len) {
    // Duplicate mono samples to both stereo channels
    size_t samples = len / 2;
    int16_t stereo[2];
    const int16_t* src = reinterpret_cast<const int16_t*>(buf);
    size_t written = 0;
    for (size_t i = 0; i < samples; i++) {
        stereo[0] = src[i];  // left
        stereo[1] = src[i];  // right
        i2s_write(I2S_PORT, stereo, 4, &written, portMAX_DELAY);
    }
}

void audio_playback_stop() {
    i2s_stop(I2S_PORT);
    i2s_driver_uninstall(I2S_PORT);
    _install_capture();
    i2s_start(I2S_PORT);
}
