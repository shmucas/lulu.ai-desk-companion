# Wiring Guide

All connections for the Lulu desk companion, built around the Seeed XIAO ESP32-S3.
Pin numbers below use the XIAO silkscreen labels (D0-D10) with the ESP32 GPIO in
parentheses, matching `firmware/src/config.h`.

## Overview

```
                        USB-C (power + flash)
                              |
                   +---------------------+
   INMP441 mic     |   XIAO ESP32-S3     |     MAX98357A amp
   ----------      |                     |     -----------
   SCK  <----------| D8  (GPIO7)         |
   WS   <----------| D9  (GPIO8)         |
   SD   ---------->| D10 (GPIO9)         |
   L/R  --> GND    |                     |
   VDD  --> 3V3    |         D1 (GPIO2)  |----------> BCLK
   GND  --> GND    |         D2 (GPIO3)  |----------> LRC
                   |         D3 (GPIO4)  |----------> DIN
   SSD1306 OLED    |                     |     VIN <-- 5V
   ------------    |                     |     GND <-- GND
   SDA  <--------->| D4  (GPIO5)         |     GAIN, SD: leave unconnected
   SCL  <----------| D5  (GPIO6)         |
   VCC  --> 3V3    |                     |         +--------+
   GND  --> GND    |         D0 (GPIO1)  |--btn--  | 4ohm3W |
                   |                     |      |  | speaker|
                   |    3V3   5V   GND   |     GND +--------+
                   +---------------------+          ^
                                                    | (+) and (-) from
                                                    | MAX98357A output
```

## INMP441 I2S microphone

| INMP441 pin | XIAO pin | Note |
|---|---|---|
| VDD | 3V3 | 3.3V only, never 5V |
| GND | GND | |
| SCK (BCLK) | D8 (GPIO7) | I2S bit clock |
| WS (LRCL) | D9 (GPIO8) | I2S word select |
| SD (DOUT) | D10 (GPIO9) | I2S data out of mic |
| L/R (SEL) | GND | Selects the left slot. Firmware reads ONLY_LEFT, so this must be tied to GND, not left floating |

## MAX98357A I2S amplifier

| MAX98357A pin | XIAO pin | Note |
|---|---|---|
| VIN | 5V | 2.5-5.5V works; 5V gives the most headroom |
| GND | GND | |
| BCLK | D1 (GPIO2) | I2S bit clock |
| LRC | D2 (GPIO3) | I2S word select |
| DIN | D3 (GPIO4) | I2S data into amp |
| GAIN | unconnected | Default 9dB. Tie to GND for 12dB, VIN for 6dB |
| SD | unconnected | Most breakout boards pull this up (amp enabled, (L+R)/2 mix) |
| + / - (speaker) | speaker | To the 4 ohm 3W speaker terminals |

## SSD1306 OLED (I2C, address 0x3C)

| OLED pin | XIAO pin | Note |
|---|---|---|
| VCC | 3V3 | |
| GND | GND | |
| SDA | D4 (GPIO5) | |
| SCL | D5 (GPIO6) | |

## Push-to-talk button

| Button leg | XIAO pin | Note |
|---|---|---|
| Leg A | D0 (GPIO1) | Firmware uses INPUT_PULLUP, active LOW |
| Leg B | GND | |

No external resistor needed - the internal pull-up is enabled in firmware.

## Power

- One USB-C cable into the XIAO powers everything.
- Mic and OLED run from the XIAO's 3V3 regulator.
- The amp runs from the 5V pin (USB pass-through) for maximum volume.
- All grounds must be common. If audio picks up hiss, keep the mic wires short
  and away from the speaker wires.

## Notes

- The XIAO ESP32-S3 has a single I2S peripheral. The firmware time-shares it:
  capture (mic) and playback (amp) are never active at the same time, which is
  why the mic and amp can use separate pins but never conflict.
- WiFi credentials and the server IP live in `firmware/src/config.h` (copy from
  `config.h.example`), not in this diagram.
