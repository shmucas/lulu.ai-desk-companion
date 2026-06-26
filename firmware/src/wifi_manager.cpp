#include <WiFi.h>
#include "wifi_manager.h"
#include "config.h"

void wifi_init() {
    Serial.print("[WiFi] connecting to ");
    Serial.println(WIFI_SSID);

    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    uint8_t attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 40) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println();
        Serial.print("[WiFi] connected, IP: ");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n[WiFi] failed - restarting");
        ESP.restart();
    }
}

bool wifi_is_connected() {
    return WiFi.status() == WL_CONNECTED;
}
