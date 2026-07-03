import re
from datetime import datetime, timedelta

import timekeeper

# The agent model often restates the duration as the label ("10 minutes") or
# appends the word "timer". Neither is a real label - scrub them.
_DURATION_ONLY = re.compile(
    r"^[\d\s.]*(minutes?|mins?|hours?|hrs?|seconds?|secs?)?[\d\s.]*$", re.IGNORECASE
)


def _clean_label(label: str) -> str:
    label = re.sub(r"\btimers?\b", "", label or "", flags=re.IGNORECASE).strip()
    if not label or _DURATION_ONLY.match(label):
        return ""
    return label


def _pretty_minutes(minutes: float) -> str:
    if minutes >= 60 and minutes % 60 == 0:
        hours = int(minutes // 60)
        return f"{hours} hour{'s' if hours != 1 else ''}"
    if minutes == int(minutes):
        m = int(minutes)
        return f"{m} minute{'s' if m != 1 else ''}"
    return f"{int(round(minutes * 60))} seconds"


def _adjective(pretty: str) -> str:
    # "10 minutes" -> "10 minute" when used before a noun ("10 minute timer")
    return pretty[:-1] if pretty.endswith("s") else pretty


class TimerTool:
    name = "set_timer"
    description = "Set a countdown timer that Lulu announces out loud when it finishes"
    side_effect = True  # scheduling twice would ring twice
    parameter_spec = {
        "minutes": {
            "type": "number",
            "description": "Duration in minutes, e.g. 10 or 1.5 for 90 seconds",
        },
        "label": {
            "type": "string",
            "description": "Short label ONLY if the user named the timer, otherwise empty string",
        },
    }

    def execute(self, minutes=None, label: str = "") -> str:
        try:
            mins = float(minutes)
        except (TypeError, ValueError):
            return "Timer needs a duration in minutes."
        if not 0 < mins <= 24 * 60:
            return "Timer duration must be between 0 and 24 hours."

        pretty = _pretty_minutes(mins)
        label = _clean_label(label)
        what = f"Your {label} timer" if label else f"Your {_adjective(pretty)} timer"
        timekeeper.schedule(mins * 60, f"Ding! {what} is done.")
        return f"Timer set for {pretty}."


class ReminderTool:
    name = "set_reminder"
    description = "Set a reminder for a specific time of day; Lulu speaks it when the time comes"
    side_effect = True
    parameter_spec = {
        "time": {
            "type": "string",
            "description": "24-hour time HH:MM, e.g. 15:30. If already past today, fires tomorrow",
        },
        "message": {
            "type": "string",
            "description": "What to remind the user about",
        },
    }

    def execute(self, time: str = "", message: str = "") -> str:
        message = (message or "").strip()
        if not message:
            return "Reminder needs a message."
        try:
            target_t = datetime.strptime(time.strip(), "%H:%M").time()
        except ValueError:
            return "Reminder time must be HH:MM in 24-hour format, e.g. 15:30."

        now = datetime.now()
        target = now.replace(hour=target_t.hour, minute=target_t.minute,
                             second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)

        timekeeper.schedule((target - now).total_seconds(), f"Reminder: {message}")
        spoken_time = target.strftime("%I:%M %p").lstrip("0")
        day = "today" if target.date() == now.date() else "tomorrow"
        return f"Reminder set for {spoken_time} {day}: {message}"
