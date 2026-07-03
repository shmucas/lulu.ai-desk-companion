"""
Timers and reminders.

Tools run in executor threads, but announcements must happen on the event
loop (they go out over the WebSocket). schedule() bridges the two with
run_coroutine_threadsafe. If the device is connected when a timer fires,
Lulu announces it there; otherwise the Mac speaks it as a fallback.

Timers are in-memory only: a backend restart clears them.
"""
import asyncio
import threading
import traceback

import tts

_loop: asyncio.AbstractEventLoop | None = None
_session = None  # active WSSession, set by main.py on connect


def init(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def set_session(session) -> None:
    global _session
    _session = session


def clear_session(session) -> None:
    global _session
    if _session is session:
        _session = None


def schedule(seconds: float, announcement: str) -> None:
    """Thread-safe: callable from tool executor threads."""
    if _loop is not None and _loop.is_running():
        asyncio.run_coroutine_threadsafe(_fire_after(seconds, announcement), _loop)
    else:
        # No server loop (e.g. tool run standalone) - speak on the Mac
        threading.Timer(seconds, tts.speak_on_mac, args=[announcement]).start()


async def _fire_after(seconds: float, announcement: str) -> None:
    await asyncio.sleep(seconds)
    print(f"[timekeeper] firing: {announcement!r}", flush=True)
    session = _session
    if session is not None:
        try:
            await session.announce(announcement)
            return
        except Exception:
            print("[timekeeper] device announce failed, falling back to Mac:\n"
                  + traceback.format_exc(), flush=True)
    await asyncio.get_event_loop().run_in_executor(None, tts.speak_on_mac, announcement)
