# Design System - Lulu

## Memorable Thing

> "A little robot that's alive, friendly, and something you'd actually talk to."

Every design decision should serve this feeling. If a change makes Lulu look more like a dashboard, a chat app, or a generic UI - reject it.

---

## Product Context

- **What this is:** A self-contained AI desk companion running on Raspberry Pi 5. Voice in, voice out. No cloud, no laptop.
- **Who it's for:** One person. The person who built it. It lives on their desk.
- **Project type:** Embedded device UI - displayed on a 3.5" IPS screen via Chromium kiosk. Also viewable from Mac browser during development.
- **Reference:** BMO from Adventure Time - small, charming, expressive, retro game console personality.

---

## Aesthetic Direction

- **Direction:** Retro-Futuristic / Phosphor CRT
- **Decoration level:** Intentional - the phosphor glow color IS the decoration. No other decoration needed.
- **Mood:** Old terminal screen that somehow grew a personality. Warm, alive, slightly nostalgic. Not cold, not sterile, not corporate.
- **What it is NOT:** A dashboard. A chat bubble. A generic assistant. A white card on a light background.

---

## Color

| Token | Value | Usage |
|---|---|---|
| `--bg` | `#060d06` | Screen background - very dark phosphor green-black |
| `--fg` | `#3dff4a` | All face elements - eyes, mouth, active UI |
| `--fg-dim` | `#1a6a1a` | Bottom bar dots, decorative separators |
| `--fg-status` | `#3dff4a` | Status label text |
| `--header-border` | `#1a3a1a` | Header and bottom bar separator lines |
| `--black` | `#000000` | Body background outside the stage |

**Color rule:** One color. `#3dff4a` on `#060d06`. That's it. Do not introduce whites, grays, blues, or accent colors. Lulu is a monochrome phosphor display.

---

## Typography

- **Display / UI:** `"Press Start 2P"` (Google Fonts) - the only font used in the entire UI
- **Size:** 8px for all text - status label, header, clock
- **Loading:** `https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap`
- **Fallback:** `monospace`

**Font rule:** Never use Inter, Roboto, Arial, or system-ui in this project. Press Start 2P is the only font. If something needs to be legible at a larger size, increase pixel count - don't switch fonts.

---

## Pixel Grid

- **Pixel unit (PX):** 4 CSS pixels - one "pixel" in the art is 4×4px on screen
- **Eye size:** 7×6 pixel-units (28×24 CSS px)
- **Eye gap:** 7 pixel-units (28px) between eye centers
- **Face Y position:** 45% of usable height (between header and bottom bar)
- **Mouth Y offset:** 10px below bottom of eye zone

**Pixel rule:** All face geometry is defined in pixel-units (multiples of 4). Never use arbitrary pixel values for face elements - everything snaps to the 4px grid.

---

## Layout

- **Canvas:** 480×320px (matches 3.5" IPS display)
- **Header bar:** 28px tall - `Lulu.ai` left, clock right
- **Bottom bar:** 28px tall - status label left, decorative dots right
- **Usable face area:** 480×264px (between bars)
- **Face centering:** Horizontally centered, 45% from top of usable area
- **Scaling:** CSS `transform: scale(min(vw/480, vh/320))` with `image-rendering: pixelated` - scales up for Mac browser without blurring

---

## Face States

| State | Eyes | Mouth | Status Label | Idle Animations |
|---|---|---|---|---|
| `standby` | Half-closed (top half blocked) | Faint smile (40% opacity) | `STANDBY` | Slow blink ~8s |
| `idle` | Open 7×6 px-units | Smile 44px wide | `IDLE` | Blink + glance + micro-saccade |
| `listening` | Wide open (+2 px-units each) | Smile 44px wide | `LISTENING...` | None - locked forward |
| `thinking` | Squinted + angled inward | Flat line 40px | `THINKING...` | None - locked |
| `speaking` | Happy arc (top curve) | Wide smile 52px | `SPEAKING...` | Eye brightness pulse |
| `error` | Drooping (bottom 2 rows only) | Frown 44px wide | `ERROR` | None |

**WebSocket contract:** `/ws` emits `{type: "status", value: "idle|standby|listening|thinking|speaking|error"}`

---

## Animation

### State transitions
- **Style:** Pixel dissolve - pixels flicker out randomly, new pixels flicker in
- **Duration:** 120ms
- **Implementation:** Canvas `ImageData` diff with shuffled pixel reveal

### Idle behaviors (IDLE and STANDBY states only)

| Behavior | Timing | Description |
|---|---|---|
| Blink | Random 3–6s | Eye height collapses to 1px over 75ms, reopens over 75ms |
| Glance | Random 8–15s | Eyes shift ±2 pixel-units, hold 1s, return over 100ms |
| Micro-saccade | Random 15–30s | ±1px shift, 200ms, return |

**Standby:** Blink interval slows to 6–10s. Glance disabled.

### Per-state animations

| State | Special animation |
|---|---|
| `speaking` | Eye opacity pulses 80%→100% on 600ms CSS keyframe loop |
| `listening` | No animation - eyes wide and locked (alert posture) |
| `thinking` | No animation - squint locked (concentration posture) |
| `error` | One slow blink on entry, then hold |

---

## Decisions Log

| Date | Decision | Rationale |
|---|---|---|
| 2026-05-27 | BMO phosphor green aesthetic | Small 3.5" screen needs strong identity. Phosphor CRT is retro-charming and unique at this form factor. |
| 2026-05-27 | Press Start 2P as sole font | Reinforces pixel-art identity. Any other font would break the CRT illusion. |
| 2026-05-27 | Face only - no text content on screen | Face IS the communication. Status label is bottom-left, small, dim. |
| 2026-05-27 | 6 states including standby | Standby defined now so Phase 3 (wake word) only needs frontend wiring, not a contract change. |
| 2026-05-27 | Pixel dissolve at 120ms | Fits retro aesthetic. CSS crossfade was rejected as too generic. |
| 2026-05-27 | Idle animations suppressed during active states | Each active expression needs to read cleanly - blinking during THINKING breaks concentration read. |
| 2026-05-27 | Eye pulse during SPEAKING | Mouth animation in pixel art looks choppy. Eye brightness pulse is subtle and works in pure CSS. |
