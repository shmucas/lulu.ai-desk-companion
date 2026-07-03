/*
 * SSD1306 128x64 face renderer for Lulu.
 *
 * Pixel unit = 2 CSS px (half the Mac UI's 4px unit).
 * All face geometry is in "art pixels" (ap), each drawn as a 2x2 fillRect.
 *
 * Face layout (128x64 display):
 *   Top margin:  6px
 *   Eyes Y:      ~26px from top (≈ 45% of 52px usable area below margin)
 *   Mouth Y:     eyes_bottom + 8px
 *   Eyes centered horizontally, separated by 14px gap between centers
 *
 * Six states from DESIGN.md, scaled to 2px pixel unit:
 *   IDLE      - open 7×6 ap eyes + smile
 *   STANDBY   - half-closed (top 3 ap blocked) + faint smile
 *   LISTENING - wide 9×7 ap eyes + smile
 *   THINKING  - squinted eyes + flat line
 *   SPEAKING  - arc eyes + wide smile
 *   ERROR     - drooping eyes + frown
 */
#include <Wire.h>
#include <time.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "display.h"
#include "config.h"
#include "wifi_manager.h"

#define PX 2  // pixel unit in display pixels

// All face geometry is authored centered around art-pixel x=21.5, but the
// display center is x=32. Shift every element right by 11 ap (22 display px)
// so the face sits centered on the 128px-wide panel.
#define OX 11  // horizontal art-pixel offset

static Adafruit_SSD1306 _oled(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
static FaceState _current_state = FaceState::IDLE;

// ── helpers ─────────────────────────────────────────────────────────────────

static void ap(int x, int y, int w, int h) {
    _oled.fillRect((x + OX) * PX, y * PX, w * PX, h * PX, SSD1306_WHITE);
}

static void draw_status(const char* label) {
    _oled.setTextSize(1);
    _oled.setTextColor(SSD1306_WHITE);
    _oled.setCursor(0, OLED_HEIGHT - 8);
    _oled.print(label);
}

static void draw_header() {
    // Top-left date/time (falls back silently if NTP hasn't synced yet)
    struct tm timeinfo;
    if (getLocalTime(&timeinfo, 10)) {
        char buf[16];
        strftime(buf, sizeof(buf), "%m/%d %H:%M", &timeinfo);
        _oled.setTextSize(1);
        _oled.setTextColor(SSD1306_WHITE);
        _oled.setCursor(2, 0);
        _oled.print(buf);
    }

    // Top-right WiFi status bars (ascending, filled when connected)
    _oled.fillRect(118, 5, 2, 2, SSD1306_WHITE);
    if (wifi_is_connected()) {
        _oled.fillRect(121, 3, 2, 4, SSD1306_WHITE);
        _oled.fillRect(124, 1, 2, 6, SSD1306_WHITE);
    }
}

// ── face drawing ─────────────────────────────────────────────────────────────
// All coordinates in art-pixel units. Origin at top-left of display.
// Display is 64×32 art pixels (128px / 2 = 64, 64px / 2 = 32).

// Eye centers in ap: left=14, right=28, Y=11 (26/2)
// Eye drawn relative to (cx - w/2, ey)

static void draw_idle() {
    _oled.clearDisplay();
    draw_header();
    // Eyes: 7×6 ap open square
    ap(11, 10, 7, 6);   // left eye
    ap(25, 10, 7, 6);   // right eye
    // Smile: 3-rect arc approximation, centered on eye midpoint (21.5 ap)
    ap(16, 18, 2, 1);
    ap(18, 19, 8, 1);
    ap(26, 18, 2, 1);
    draw_status("IDLE");
    _oled.display();
}

static void draw_standby() {
    _oled.clearDisplay();
    draw_header();
    // Eyes: top 3 ap blocked (half-closed - droopy)
    ap(11, 13, 7, 3);   // left eye (only bottom half visible)
    ap(25, 13, 7, 3);   // right eye
    // Faint smile (dimmer - draw dots only), centered on eye midpoint
    ap(17, 18, 1, 1);
    ap(19, 19, 6, 1);
    ap(25, 18, 1, 1);
    draw_status("STANDBY");
    _oled.display();
}

static void draw_listening() {
    _oled.clearDisplay();
    draw_header();
    // Eyes: wide 9×7 ap (alert)
    ap(10, 9, 9, 7);    // left eye
    ap(24, 9, 9, 7);    // right eye
    // Smile same as idle, centered on eye midpoint
    ap(16, 18, 2, 1);
    ap(18, 19, 8, 1);
    ap(26, 18, 2, 1);
    draw_status("LISTENING...");
    _oled.display();
}

static void draw_thinking() {
    _oled.clearDisplay();
    draw_header();
    // Eyes: squinted - only bottom 2 ap rows, angled inward
    // left eye: bottom-left corner angled
    ap(11, 13, 5, 2);
    ap(13, 15, 3, 1);
    // right eye: bottom-right corner angled (mirror)
    ap(27, 13, 5, 2);
    ap(27, 15, 3, 1);
    // Flat line mouth, centered on eye midpoint
    ap(17, 19, 10, 1);
    draw_status("THINKING...");
    _oled.display();
}

static void draw_speaking() {
    _oled.clearDisplay();
    draw_header();
    // Eyes: happy arc (top curve only, no box)
    // Left eye arc: 3 segments
    ap(13, 11, 3, 2);
    ap(11, 12, 2, 2);
    ap(16, 12, 2, 2);
    // Right eye arc
    ap(27, 11, 3, 2);
    ap(25, 12, 2, 2);
    ap(30, 12, 2, 2);
    // Wide smile: 26ap wide, centered on eye midpoint
    ap(15, 18, 2, 1);
    ap(17, 19, 10, 2);
    ap(27, 18, 2, 1);
    draw_status("SPEAKING...");
    _oled.display();
}

static void draw_error() {
    _oled.clearDisplay();
    draw_header();
    // Eyes: drooping - bottom 2 ap rows only
    ap(11, 14, 7, 2);   // left
    ap(25, 14, 7, 2);   // right
    // Frown, centered on eye midpoint
    ap(16, 19, 2, 1);
    ap(18, 18, 8, 1);
    ap(26, 19, 2, 1);
    draw_status("ERROR");
    _oled.display();
}

// ── public API ───────────────────────────────────────────────────────────────

void display_init() {
    Wire.begin(OLED_SDA_PIN, OLED_SCL_PIN);
    if (!_oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
        Serial.println("[OLED] init failed");
        return;
    }
    _oled.ssd1306_command(SSD1306_SETCONTRAST);
    _oled.ssd1306_command(0xFF);  // maximum brightness
    _oled.clearDisplay();
    _oled.display();
    Serial.println("[OLED] ready");
}

void display_set_state(FaceState state) {
    if (state == _current_state) return;
    _current_state = state;
    switch (state) {
        case FaceState::IDLE:        draw_idle();      break;
        case FaceState::STANDBY:     draw_standby();   break;
        case FaceState::LISTENING:   draw_listening(); break;
        case FaceState::THINKING:    draw_thinking();  break;
        case FaceState::SPEAKING:    draw_speaking();  break;
        case FaceState::ERROR_STATE: draw_error();     break;
    }
}
