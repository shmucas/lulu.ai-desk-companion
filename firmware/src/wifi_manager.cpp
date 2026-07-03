#include <WiFi.h>
#include "wifi_manager.h"
#include "config.h"

void wifi_init() {
    Serial.print("[WiFi] connecting to ");
    Serial.println(WIFI_SSID);

    // Clear any stale config and disable persistence so a wrong saved
    // network never overrides config.h on boot.
    WiFi.persistent(false);
    WiFi.disconnect(true, true);
    delay(200);

    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);   // sleep can break association on some routers
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    uint8_t attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 60) {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println();
        Serial.print("[WiFi] connected, IP: ");
        Serial.println(WiFi.localIP());
        configTzTime(TIME_ZONE, NTP_SERVER);
    } else {
        Serial.println();
        Serial.print("[WiFi] failed, status code: ");
        Serial.println(WiFi.status());
        Serial.println("[WiFi] restarting...");
        ESP.restart();
    }
}

bool wifi_is_connected() {
    return WiFi.status() == WL_CONNECTED;
}
