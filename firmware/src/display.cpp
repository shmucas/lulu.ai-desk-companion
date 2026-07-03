/*
 * SSD1306 128x64 face renderer for Lulu.
 *
 * Pixel unit = 2 CSS px (half the Mac UI's 4px unit).
 * All face geometry is in "art pixels" (ap), each drawn as a 2x2 fillRect.
 *
 * Face layout (128x64 display):
 *   Top margin:  6px
 *   Eyes Y:      ~26px from top
 *   Mouth Y:     eyes_bottom + 8px
 *   Eyes centered horizontally, separated by 14px gap between centers
 *
 * Six states from DESIGN.md, scaled to 2px pixel unit:
 *   IDLE      - open 7x6 ap eyes + smile.  Animates: blink 3-6s, glance 8-15s
 *   STANDBY   - half-closed eyes + faint smile.  Animates: slow blink 6-10s
 *   LISTENING - wide 9x7 ap eyes + smile.  Locked, no animation
 *   THINKING  - squinted eyes + flat line.  Locked, no animation
 *   SPEAKING  - arc eyes + mouth cycling between smile and open "O" (~160ms)
 *   ERROR     - drooping eyes + frown.  Static
 *
 * All animation runs through display_tick(), called from loop(). Nothing
 * blocks: each tick either redraws one frame or returns immediately.
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

// Animation timing (ms)
#define BLINK_HOLD_MS      120   // how long eyes stay shut mid-blink
#define GLANCE_HOLD_MS    1000   // how long a glance holds before returning
#define MOUTH_FRAME_MS     160   // speaking mouth cycle half-period
#define CLOCK_REFRESH_MS 30000   // header clock refresh while idle

static Adafruit_SSD1306 _oled(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
static FaceState _state = FaceState::IDLE;

// Animation state
static bool _eyes_closed = false;
static int  _eye_dx = 0;          // glance offset in art pixels
static int  _mouth_frame = 0;     // speaking: 0 = smile, 1 = open
static unsigned long _next_blink = 0;
static unsigned long _blink_until = 0;
static unsigned long _next_glance = 0;
static unsigned long _glance_until = 0;
static unsigned long _next_mouth = 0;
static unsigned long _next_clock = 0;

// ── helpers ─────────────────────────────────────────────────────────────────

static void ap(int x, int y, int w, int h) {
    _oled.fillRect((x + OX) * PX, y * PX, w * PX, h * PX, SSD1306_WHITE);
}

static void _schedule_blink(unsigned long now) {
    if (_state == FaceState::STANDBY) {
        _next_blink = now + random(6000, 10000);
    } else {
        _next_blink = now + random(3000, 6000);
    }
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

// ── face parts ───────────────────────────────────────────────────────────────
// All coordinates in art-pixel units. Origin at top-left of display.
// Display is 64x32 art pixels (128px / 2 = 64, 64px / 2 = 32).

static void _smile() {
    // 3-rect arc approximation, centered on eye midpoint (21.5 ap)
    ap(16, 18, 2, 1);
    ap(18, 19, 8, 1);
    ap(26, 18, 2, 1);
}

static void _face_idle() {
    if (_eyes_closed) {
        // Blink: eyes collapse to a 1-ap bar at eye vertical center
        ap(11 + _eye_dx, 13, 7, 1);
        ap(25 + _eye_dx, 13, 7, 1);
    } else {
        ap(11 + _eye_dx, 10, 7, 6);   // left eye
        ap(25 + _eye_dx, 10, 7, 6);   // right eye
    }
    _smile();
}

static void _face_standby() {
    if (_eyes_closed) {
        ap(11, 15, 7, 1);
        ap(25, 15, 7, 1);
    } else {
        // Half-closed (top blocked - droopy)
        ap(11, 13, 7, 3);
        ap(25, 13, 7, 3);
    }
    // Faint smile (dots only), centered on eye midpoint
    ap(17, 18, 1, 1);
    ap(19, 19, 6, 1);
    ap(25, 18, 1, 1);
}

static void _face_listening() {
    // Eyes: wide 9x7 ap (alert), locked forward
    ap(10, 9, 9, 7);
    ap(24, 9, 9, 7);
    _smile();
}

static void _face_thinking() {
    // Eyes: squinted - only bottom rows, angled inward
    ap(11, 13, 5, 2);
    ap(13, 15, 3, 1);
    ap(27, 13, 5, 2);
    ap(27, 15, 3, 1);
    // Flat line mouth, centered on eye midpoint
    ap(17, 19, 10, 1);
}

static void _face_speaking() {
    // Eyes: happy arc (top curve only, no box)
    ap(13, 11, 3, 2);
    ap(11, 12, 2, 2);
    ap(16, 12, 2, 2);
    ap(27, 11, 3, 2);
    ap(25, 12, 2, 2);
    ap(30, 12, 2, 2);
    if (_mouth_frame == 0) {
        // Wide smile, centered on eye midpoint
        ap(15, 18, 2, 1);
        ap(17, 19, 10, 2);
        ap(27, 18, 2, 1);
    } else {
        // Open "O" mouth
        ap(19, 17, 6, 1);
        ap(18, 18, 8, 2);
        ap(19, 20, 6, 1);
    }
}

static void _face_error() {
    // Eyes: drooping - bottom rows only
    ap(11, 14, 7, 2);
    ap(25, 14, 7, 2);
    // Frown, centered on eye midpoint
    ap(16, 19, 2, 1);
    ap(18, 18, 8, 1);
    ap(26, 19, 2, 1);
}

// ── rendering ────────────────────────────────────────────────────────────────

static void _render() {
    _oled.clearDisplay();
    draw_header();
    switch (_state) {
        case FaceState::IDLE:        _face_idle();      draw_status("IDLE");         break;
        case FaceState::STANDBY:     _face_standby();   draw_status("STANDBY");      break;
        case FaceState::LISTENING:   _face_listening(); draw_status("LISTENING..."); break;
        case FaceState::THINKING:    _face_thinking();  draw_status("THINKING...");  break;
        case FaceState::SPEAKING:    _face_speaking();  draw_status("SPEAKING...");  break;
        case FaceState::ERROR_STATE: _face_error();     draw_status("ERROR");        break;
    }
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
    randomSeed(esp_random());
    Serial.println("[OLED] ready");
}

void display_set_state(FaceState state) {
    if (state == _state) return;
    _state = state;

    // Reset animation state on every transition
    unsigned long now = millis();
    _eyes_closed = false;
    _eye_dx = 0;
    _mouth_frame = 0;
    _schedule_blink(now);
    _next_glance = now + random(8000, 15000);
    _next_mouth = now + MOUTH_FRAME_MS;
    _next_clock = now + CLOCK_REFRESH_MS;

    _render();
}

void display_tick() {
    unsigned long now = millis();

    switch (_state) {
        case FaceState::IDLE:
        case FaceState::STANDBY: {
            bool dirty = false;

            // Blink
            if (!_eyes_closed && now >= _next_blink) {
                _eyes_closed = true;
                _blink_until = now + BLINK_HOLD_MS;
                dirty = true;
            } else if (_eyes_closed && now >= _blink_until) {
                _eyes_closed = false;
                _schedule_blink(now);
                dirty = true;
            }

            // Glance (IDLE only - standby is too sleepy to look around)
            if (_state == FaceState::IDLE) {
                if (_eye_dx == 0 && now >= _next_glance) {
                    _eye_dx = random(2) ? 2 : -2;
                    _glance_until = now + GLANCE_HOLD_MS;
                    dirty = true;
                } else if (_eye_dx != 0 && now >= _glance_until) {
                    _eye_dx = 0;
                    _next_glance = now + random(8000, 15000);
                    dirty = true;
                }
            }

            // Keep the header clock fresh
            if (now >= _next_clock) {
                _next_clock = now + CLOCK_REFRESH_MS;
                dirty = true;
            }

            if (dirty) _render();
            break;
        }

        case FaceState::SPEAKING:
            if (now >= _next_mouth) {
                _mouth_frame ^= 1;
                _next_mouth = now + MOUTH_FRAME_MS;
                _render();
            }
            break;

        default:
            // LISTENING and THINKING are locked poses; ERROR is static
            break;
    }
}
