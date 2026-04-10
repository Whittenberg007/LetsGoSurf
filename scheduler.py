import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

APP_DIR = os.path.dirname(os.path.abspath(__file__))
JOBS_PATH = os.path.join(APP_DIR, "scheduled_jobs.json")
LOG_PATH = os.path.join(APP_DIR, "scheduled_log.txt")

DAY_NAMES = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def _get_now() -> datetime:
    """Get the current datetime. Extracted for testability."""
    return datetime.now()


def parse_schedule_time(text: str) -> datetime | None:
    """Parse a schedule time string into a future datetime.

    Accepts:
      - "Sunday 7am", "saturday 6:30pm", "tomorrow 6am"
      - "2026-04-19 07:00"

    Returns None if the input is invalid or in the past.
    """
    text = text.strip()
    if not text:
        return None

    now = _get_now()

    # Try explicit format: "2026-04-19 07:00"
    try:
        dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
        return dt if dt > now else None
    except ValueError:
        pass

    # Try "day time" format: "Sunday 7am", "tomorrow 6:30pm"
    parts = text.lower().split()
    if len(parts) != 2:
        return None

    day_str, time_str = parts

    # Parse time component: "7am", "6:30pm", "12pm"
    parsed_time = _parse_time(time_str)
    if parsed_time is None:
        return None
    hour, minute = parsed_time

    # Parse day component
    if day_str == "tomorrow":
        target_date = now.date() + timedelta(days=1)
    elif day_str in DAY_NAMES:
        target_day = DAY_NAMES[day_str]
        current_day = now.weekday()
        days_ahead = (target_day - current_day) % 7

        target_date = now.date() + timedelta(days=days_ahead)
        target_dt = datetime(target_date.year, target_date.month, target_date.day, hour, minute)

        # If it's the same day but time has passed, go to next week
        if days_ahead == 0 and target_dt <= now:
            target_date = now.date() + timedelta(days=7)
    else:
        return None

    result = datetime(target_date.year, target_date.month, target_date.day, hour, minute)
    return result if result > now else None


def _parse_time(time_str: str) -> tuple | None:
    """Parse '7am', '6:30pm', '12pm' into (hour, minute). Returns None on failure."""
    time_str = time_str.lower().strip()

    if time_str.endswith("am"):
        suffix = "am"
        time_str = time_str[:-2]
    elif time_str.endswith("pm"):
        suffix = "pm"
        time_str = time_str[:-2]
    else:
        return None

    if ":" in time_str:
        parts = time_str.split(":")
        if len(parts) != 2:
            return None
        try:
            hour = int(parts[0])
            minute = int(parts[1])
        except ValueError:
            return None
    else:
        try:
            hour = int(time_str)
            minute = 0
        except ValueError:
            return None

    if not (1 <= hour <= 12 and 0 <= minute <= 59):
        return None

    # Convert 12-hour to 24-hour
    if suffix == "am":
        if hour == 12:
            hour = 0
    else:
        if hour != 12:
            hour += 12

    return hour, minute
