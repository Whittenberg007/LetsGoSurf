# Scheduled Surf Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the ability to schedule a future surf conditions check that runs automatically via Windows Task Scheduler, fetches live data at the scheduled time, and sends results to a contact (and the user).

**Architecture:** A new `scheduler.py` module handles job persistence (`scheduled_jobs.json`), date parsing, Windows Task Scheduler integration (`schtasks.exe` via `subprocess`), and headless execution. `surf_finder.py` gains a `--run-scheduled` CLI entry point and a new "Scheduled checks" submenu. Core surf-finding logic is extracted from `find_waves()` into reusable functions that both the interactive and headless paths call.

**Tech Stack:** Python 3.7+ stdlib only (`datetime`, `subprocess`, `json`, `sys`). No new dependencies.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `scheduler.py` | **Create** | Job CRUD, date parsing, Windows Task Scheduler wrapper, headless execution orchestration |
| `surf_finder.py` | **Modify** | Extract shared logic into functions, add `--run-scheduled` CLI handling, add "Scheduled checks" menu option |
| `tests/test_scheduler.py` | **Create** | Tests for date parsing, job CRUD, task scheduler calls, headless execution |
| `tests/test_surf_finder.py` | **Create** | Tests for extracted pure logic functions (`fetch_matching_spots`, `build_full_list_message`) |
| `scheduled_jobs.json` | **Runtime** | Created on first schedule (not committed) |
| `scheduled_log.txt` | **Runtime** | Created on first headless run (not committed) |

---

### Task 1: Extract `fetch_matching_spots()` from `find_waves()`

**Files:**
- Create: `tests/test_surf_finder.py`
- Modify: `surf_finder.py:47-135`

This task extracts the core "filter by distance, fetch conditions, filter by wave range" logic into a standalone function. This is the foundation that both the interactive and headless paths will call.

- [ ] **Step 1: Write the failing test for `fetch_matching_spots`**

Create `tests/test_surf_finder.py`:

```python
from unittest.mock import patch, MagicMock
from surf_finder import fetch_matching_spots


def test_fetch_matching_spots_returns_matches():
    """Spots within radius with matching wave range are returned."""
    spots = [
        {"name": "Spot A", "lat": 33.6, "lon": -117.9, "surfline_id": "abc123"},
        {"name": "Spot B", "lat": 33.7, "lon": -117.8, "surfline_id": "def456"},
    ]
    mock_conditions = {
        "wave_min": 2, "wave_max": 3,
        "condition_rating": "Fair", "condition_rank": 4,
        "tide_trend": "Rising", "wind_direction_type": "Offshore",
        "wave_human": "", "wind_speed": 5,
    }

    with patch("surf_finder.get_surfline_conditions", return_value=mock_conditions):
        results = fetch_matching_spots(
            spots=spots,
            user_lat=33.65, user_lon=-117.85,
            radius=30, wave_range=(2.0, 3.0),
        )

    assert len(results) == 2
    # Each result is (spot, conditions, distance)
    assert results[0][0]["name"] in ("Spot A", "Spot B")
    assert results[0][1]["wave_min"] == 2
    assert isinstance(results[0][2], float)


def test_fetch_matching_spots_filters_by_distance():
    """Spots outside radius are excluded."""
    spots = [
        {"name": "Near", "lat": 33.65, "lon": -117.85, "surfline_id": "abc"},
        {"name": "Far", "lat": 40.0, "lon": -120.0, "surfline_id": "def"},
    ]
    mock_conditions = {
        "wave_min": 2, "wave_max": 3,
        "condition_rating": "Fair", "condition_rank": 4,
        "tide_trend": "Rising", "wind_direction_type": "Offshore",
        "wave_human": "", "wind_speed": 5,
    }

    with patch("surf_finder.get_surfline_conditions", return_value=mock_conditions):
        results = fetch_matching_spots(
            spots=spots,
            user_lat=33.65, user_lon=-117.85,
            radius=30, wave_range=(2.0, 3.0),
        )

    assert len(results) == 1
    assert results[0][0]["name"] == "Near"


def test_fetch_matching_spots_no_wave_match_returns_all_nearby():
    """When no spots match wave range, all nearby spots with conditions are returned."""
    spots = [
        {"name": "Spot A", "lat": 33.65, "lon": -117.85, "surfline_id": "abc"},
    ]
    mock_conditions = {
        "wave_min": 5, "wave_max": 7,
        "condition_rating": "Good", "condition_rank": 6,
        "tide_trend": "Falling", "wind_direction_type": "Offshore",
        "wave_human": "", "wind_speed": 3,
    }

    with patch("surf_finder.get_surfline_conditions", return_value=mock_conditions):
        results = fetch_matching_spots(
            spots=spots,
            user_lat=33.65, user_lon=-117.85,
            radius=30, wave_range=(2.0, 3.0),
        )

    # Returns all nearby even though wave range doesn't match
    assert len(results) == 1
    assert results[0][0]["name"] == "Spot A"


def test_fetch_matching_spots_uses_openmeteo_fallback():
    """Spots without surfline_id use Open-Meteo API."""
    spots = [
        {"name": "No Surfline", "lat": 33.65, "lon": -117.85},
    ]
    mock_conditions = {
        "wave_min": 2, "wave_max": 3,
        "condition_rating": "N/A", "condition_rank": 4,
        "tide_trend": "Unknown", "wind_direction_type": "Unknown",
        "wave_human": "", "wind_speed": 0,
    }

    with patch("surf_finder.get_surfline_conditions") as mock_surfline, \
         patch("surf_finder.get_openmeteo_conditions", return_value=mock_conditions) as mock_meteo:
        results = fetch_matching_spots(
            spots=spots,
            user_lat=33.65, user_lon=-117.85,
            radius=30, wave_range=(2.0, 3.0),
        )

    mock_surfline.assert_not_called()
    mock_meteo.assert_called_once()
    assert len(results) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_surf_finder.py -v`
Expected: FAIL with `ImportError: cannot import name 'fetch_matching_spots'`

- [ ] **Step 3: Implement `fetch_matching_spots` in `surf_finder.py`**

Add this function after the `ranges_overlap` function (after line 44):

```python
def fetch_matching_spots(spots: list, user_lat: float, user_lon: float,
                         radius: float, wave_range: tuple) -> list:
    """Filter spots by distance, fetch conditions, return all nearby with conditions.

    Returns list of (spot, conditions, distance) tuples sorted by distance.
    Fetches from Surfline if spot has surfline_id, else Open-Meteo.
    """
    desired_min, desired_max = wave_range

    # Filter by distance
    nearby = []
    for spot in spots:
        dist = haversine_miles(user_lat, user_lon, spot["lat"], spot["lon"])
        if dist <= radius:
            nearby.append((spot, dist))

    # Fetch conditions for all nearby spots
    all_conditions = []
    for spot, dist in nearby:
        if spot.get("surfline_id"):
            conditions = get_surfline_conditions(spot["surfline_id"])
        else:
            conditions = get_openmeteo_conditions(spot["lat"], spot["lon"])

        if conditions:
            all_conditions.append((spot, conditions, dist))

    # Filter to matching wave size
    matches = [
        (spot, cond, dist) for spot, cond, dist in all_conditions
        if ranges_overlap(desired_min, desired_max, cond["wave_min"], cond["wave_max"])
    ]

    # If matches exist, return only matches; otherwise return all nearby
    results = matches if matches else all_conditions
    results.sort(key=lambda x: x[2])
    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_surf_finder.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Refactor `find_waves()` to use `fetch_matching_spots()`**

Replace lines 100-163 of `surf_finder.py` (from `radius = config.get(...)` through the wave suggestion block) with:

```python
    radius = config.get("default_radius_miles", 30)
    print(f"\n  Checking conditions for spots within {radius}mi...")

    results = fetch_matching_spots(spots, user_lat, user_lon, radius, wave_range)

    if not results:
        print(f"\n  Could not fetch conditions for any spots near {location_name}.")
        print("  Surfline may be down. Try again in a minute.")
        return contacts

    # Check if any results are exact wave matches
    has_exact_matches = any(
        ranges_overlap(desired_min, desired_max, cond["wave_min"], cond["wave_max"])
        for _, cond, _ in results
    )

    if has_exact_matches:
        print(f"\n  Surf spots with {wave_input}ft waves within {radius}mi of {location_name}:\n")
    else:
        print(f"\n  No spots with exactly {wave_input}ft waves near {location_name}.")
        print(f"  Here's what's currently out there ({len(results)} spots):\n")

    header = f"  {'#':<4}{'Spot':<26}{'Waves':<10}{'Conditions':<14}{'Tide':<10}{'Wind':<12}{'Parking':<18}{'Distance':<10}Directions"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for i, (spot, cond, dist) in enumerate(results):
        waves = f"{cond['wave_min']}-{cond['wave_max']} ft"
        url = directions_url(spot)
        parking = spot.get("parking_cost", "Unknown")
        print(f"  {i+1:<4}{spot['name']:<26}{waves:<10}{cond['condition_rating']:<14}{cond['tide_trend']:<10}{cond['wind_direction_type']:<12}{parking:<18}{dist:<10.1f}{url}")

    if has_exact_matches:
        print(f"\n  Found {len(results)} spots matching your criteria.")
    else:
        wave_sizes = set()
        for _, cond, _ in results:
            low = int(cond["wave_min"])
            high = max(low + 1, int(cond["wave_max"]) + 1)
            wave_sizes.add(f"{low}-{high}")
        if wave_sizes:
            print(f"\n  Try these wave ranges: {', '.join(sorted(wave_sizes))}ft")
```

- [ ] **Step 6: Run full test suite to verify no regressions**

Run: `pytest tests/ -v`
Expected: All existing tests PASS

- [ ] **Step 7: Commit**

```bash
git add surf_finder.py tests/test_surf_finder.py
git commit -m "refactor: extract fetch_matching_spots from find_waves

Pulls distance filtering, condition fetching, and wave range matching
into a reusable function for both interactive and scheduled paths."
```

---

### Task 2: Extract `build_full_list_message()`

**Files:**
- Modify: `tests/test_surf_finder.py`
- Modify: `surf_finder.py:275-294`

Extract the multi-spot message building logic so the headless path can reuse it.

- [ ] **Step 1: Write the failing test for `build_full_list_message`**

Append to `tests/test_surf_finder.py`:

```python
from surf_finder import build_full_list_message


def test_build_full_list_message_single_spot():
    results = [
        (
            {"name": "Trestles", "parking_cost": "Free",
             "lat": 33.38, "lon": -117.59,
             "parking_lat": 33.38, "parking_lon": -117.59},
            {"wave_min": 2, "wave_max": 3,
             "condition_rating": "Good", "condition_rank": 6,
             "tide_trend": "Rising", "wind_direction_type": "Offshore",
             "wave_human": "", "wind_speed": 5},
            12.3,
        ),
    ]
    subject, body = build_full_list_message(results, "Santa Ana, CA", "android")
    assert "1 spots" in subject or "1 spot" in subject
    assert "Santa Ana" in subject
    assert "Trestles" in body
    assert "2-3" in body
    assert "Good" in body
    assert "google.com/maps" in body


def test_build_full_list_message_multiple_spots():
    spot_a = {"name": "Spot A", "parking_cost": "Free",
              "lat": 33.0, "lon": -117.0,
              "parking_lat": 33.0, "parking_lon": -117.0}
    spot_b = {"name": "Spot B", "parking_cost": "$15/day",
              "lat": 33.1, "lon": -117.1,
              "parking_lat": 33.1, "parking_lon": -117.1}
    cond = {"wave_min": 3, "wave_max": 4,
            "condition_rating": "Fair", "condition_rank": 4,
            "tide_trend": "Falling", "wind_direction_type": "Onshore",
            "wave_human": "", "wind_speed": 8}

    results = [(spot_a, cond, 5.0), (spot_b, cond, 10.0)]
    subject, body = build_full_list_message(results, "92704", "iphone")
    assert "2 spots" in subject
    assert "Spot A" in body
    assert "Spot B" in body
    assert "apple.com" in body  # iPhone gets Apple Maps


def test_build_full_list_message_iphone_vs_android():
    spot = {"name": "Test", "parking_cost": "Free",
            "lat": 33.0, "lon": -117.0,
            "parking_lat": 33.0, "parking_lon": -117.0}
    cond = {"wave_min": 2, "wave_max": 3,
            "condition_rating": "Fair", "condition_rank": 4,
            "tide_trend": "Rising", "wind_direction_type": "Offshore",
            "wave_human": "", "wind_speed": 5}

    _, body_android = build_full_list_message([(spot, cond, 5.0)], "Test", "android")
    _, body_iphone = build_full_list_message([(spot, cond, 5.0)], "Test", "iphone")
    assert "google.com/maps" in body_android
    assert "maps.apple.com" in body_iphone
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_surf_finder.py::test_build_full_list_message_single_spot -v`
Expected: FAIL with `ImportError: cannot import name 'build_full_list_message'`

- [ ] **Step 3: Implement `build_full_list_message` in `surf_finder.py`**

Add after `fetch_matching_spots()`:

```python
def build_full_list_message(results: list, location_name: str, device: str = "android") -> tuple:
    """Build subject and body for a multi-spot surf report. Returns (subject, body)."""
    subject = f"Surf Report: {len(results)} spots near {location_name}"
    lines = [f"Surf spots near {location_name}:", ""]
    for i, (spot, cond, dist) in enumerate(results):
        url = directions_url(spot, device)
        parking = spot.get("parking_cost", "Unknown")
        lines.append(f"{i+1}. {spot['name']} — {cond['wave_min']}-{cond['wave_max']}ft, {cond['condition_rating']}")
        lines.append(f"   Tide: {cond['tide_trend']} | Wind: {cond['wind_direction_type']}")
        lines.append(f"   Parking: {parking} | {dist:.1f}mi away")
        lines.append(f"   {url}")
        lines.append("")
    return subject, "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_surf_finder.py -v`
Expected: All tests PASS

- [ ] **Step 5: Refactor `find_waves()` to use `build_full_list_message()`**

Replace the inline message-building block in `find_waves()` (the `if len(spots_to_send) == 1: ... else:` block around lines 275-294) with:

```python
    if len(spots_to_send) == 1:
        spot, cond, dist = spots_to_send[0]
        url = directions_url(spot, device)
        subject, body = build_spot_message(spot, cond, url)
        send_label = spot["name"]
    else:
        subject, body = build_full_list_message(spots_to_send, location_name, device)
        send_label = f"{len(spots_to_send)} spots"
```

- [ ] **Step 6: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add surf_finder.py tests/test_surf_finder.py
git commit -m "refactor: extract build_full_list_message from find_waves

Reusable message builder for multi-spot surf reports, used by both
interactive send and upcoming scheduled execution path."
```

---

### Task 3: Implement `parse_schedule_time()`

**Files:**
- Create: `scheduler.py`
- Create: `tests/test_scheduler.py`

This is the trickiest logic — parsing human-friendly time inputs like "Sunday 7am" into datetimes.

- [ ] **Step 1: Write the failing tests for `parse_schedule_time`**

Create `tests/test_scheduler.py`:

```python
from datetime import datetime
from unittest.mock import patch
from scheduler import parse_schedule_time


def _mock_now(year, month, day, hour=12, minute=0):
    """Return a patcher that fixes datetime.now() to a specific time."""
    fixed = datetime(year, month, day, hour, minute, 0)
    return patch("scheduler.datetime", wraps=datetime, **{
        "now.return_value": fixed,
    })


class TestParseScheduleTime:
    def test_explicit_datetime(self):
        with _mock_now(2026, 4, 9, 20, 0):
            result = parse_schedule_time("2026-04-19 07:00")
        assert result == datetime(2026, 4, 19, 7, 0)

    def test_day_name_and_time_am(self):
        # Wednesday Apr 9 2026 at 8pm -> "Sunday 7am" = Apr 13 2026 07:00
        with _mock_now(2026, 4, 9, 20, 0):
            result = parse_schedule_time("Sunday 7am")
        assert result == datetime(2026, 4, 13, 7, 0)

    def test_day_name_case_insensitive(self):
        with _mock_now(2026, 4, 9, 20, 0):
            result = parse_schedule_time("sunday 7am")
        assert result == datetime(2026, 4, 13, 7, 0)

    def test_day_name_pm_time(self):
        with _mock_now(2026, 4, 9, 20, 0):
            result = parse_schedule_time("saturday 6:30pm")
        assert result == datetime(2026, 4, 11, 18, 30)

    def test_tomorrow(self):
        with _mock_now(2026, 4, 9, 20, 0):
            result = parse_schedule_time("tomorrow 6am")
        assert result == datetime(2026, 4, 10, 6, 0)

    def test_same_day_future_time(self):
        # Sunday at 6am, scheduling "Sunday 7am" -> today (not next week)
        with _mock_now(2026, 4, 12, 6, 0):  # Sunday Apr 12
            result = parse_schedule_time("Sunday 7am")
        assert result == datetime(2026, 4, 12, 7, 0)

    def test_same_day_past_time_goes_to_next_week(self):
        # Sunday at 8am, scheduling "Sunday 7am" -> next Sunday
        with _mock_now(2026, 4, 12, 8, 0):  # Sunday Apr 12
            result = parse_schedule_time("Sunday 7am")
        assert result == datetime(2026, 4, 19, 7, 0)

    def test_past_explicit_datetime_returns_none(self):
        with _mock_now(2026, 4, 9, 20, 0):
            result = parse_schedule_time("2026-04-08 07:00")
        assert result is None

    def test_invalid_input_returns_none(self):
        with _mock_now(2026, 4, 9, 20, 0):
            assert parse_schedule_time("not a date") is None
            assert parse_schedule_time("") is None
            assert parse_schedule_time("7am") is None

    def test_12pm_is_noon(self):
        with _mock_now(2026, 4, 9, 8, 0):
            result = parse_schedule_time("Saturday 12pm")
        assert result == datetime(2026, 4, 11, 12, 0)

    def test_12am_is_midnight(self):
        with _mock_now(2026, 4, 9, 8, 0):
            result = parse_schedule_time("Saturday 12am")
        assert result == datetime(2026, 4, 11, 0, 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scheduler.py::TestParseScheduleTime -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'scheduler'`

- [ ] **Step 3: Implement `parse_schedule_time` in `scheduler.py`**

Create `scheduler.py`:

```python
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

    now = datetime.now()

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scheduler.py::TestParseScheduleTime -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
git add scheduler.py tests/test_scheduler.py
git commit -m "feat: add parse_schedule_time for natural date input

Parses 'Sunday 7am', 'tomorrow 6:30pm', and '2026-04-19 07:00'
into datetime objects. Handles same-day edge cases and past time
rejection."
```

---

### Task 4: Implement Job CRUD (`load_jobs`, `save_jobs`, `schedule_job`, `cancel_job`)

**Files:**
- Modify: `scheduler.py`
- Modify: `tests/test_scheduler.py`

- [ ] **Step 1: Write the failing tests for job CRUD**

Append to `tests/test_scheduler.py`:

```python
import os
import json
import tempfile
from scheduler import load_jobs, save_jobs, schedule_job, cancel_job


class TestJobCrud:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.jobs_path = os.path.join(self.tmpdir, "scheduled_jobs.json")

    def test_load_jobs_empty_when_no_file(self):
        result = load_jobs(self.jobs_path)
        assert result == []

    def test_save_and_load_jobs(self):
        jobs = [{"job_id": "surf_20260419_070000", "location": "92704"}]
        save_jobs(jobs, self.jobs_path)
        loaded = load_jobs(self.jobs_path)
        assert loaded == jobs

    def test_schedule_job_creates_entry(self):
        with patch("scheduler.subprocess.run") as mock_run, \
             patch("scheduler.JOBS_PATH", self.jobs_path):
            mock_run.return_value = MagicMock(returncode=0)

            job = schedule_job(
                scheduled_time=datetime(2026, 4, 19, 7, 0),
                location="92704",
                wave_range="2-3",
                radius_miles=30,
                region="socal",
                contact_name="Brian",
                send_method="3",
                jobs_path=self.jobs_path,
            )

        assert job["job_id"] == "surf_20260419_070000"
        assert job["location"] == "92704"
        assert job["contact_name"] == "Brian"
        assert job["task_name"] == "LetsGoSurf_surf_20260419_070000"

        # Verify persisted
        saved = load_jobs(self.jobs_path)
        assert len(saved) == 1
        assert saved[0]["job_id"] == "surf_20260419_070000"

    def test_schedule_job_calls_schtasks_create(self):
        with patch("scheduler.subprocess.run") as mock_run, \
             patch("scheduler.JOBS_PATH", self.jobs_path):
            mock_run.return_value = MagicMock(returncode=0)

            schedule_job(
                scheduled_time=datetime(2026, 4, 19, 7, 0),
                location="92704",
                wave_range="2-3",
                radius_miles=30,
                region="socal",
                contact_name="Brian",
                send_method="3",
                jobs_path=self.jobs_path,
            )

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "schtasks"
        assert "/create" in call_args
        assert "LetsGoSurf_surf_20260419_070000" in call_args

    def test_schedule_job_rejects_duplicate(self):
        # Pre-populate a job with the same time
        existing = [{"job_id": "surf_20260419_070000", "location": "92704"}]
        save_jobs(existing, self.jobs_path)

        with patch("scheduler.subprocess.run") as mock_run:
            import pytest
            with pytest.raises(ValueError, match="already exists"):
                schedule_job(
                    scheduled_time=datetime(2026, 4, 19, 7, 0),
                    location="92704",
                    wave_range="2-3",
                    radius_miles=30,
                    region="socal",
                    contact_name="Brian",
                    send_method="3",
                    jobs_path=self.jobs_path,
                )
        mock_run.assert_not_called()

    def test_cancel_job_removes_entry(self):
        # Pre-populate a job
        jobs = [{
            "job_id": "surf_20260419_070000",
            "task_name": "LetsGoSurf_surf_20260419_070000",
            "location": "92704",
        }]
        save_jobs(jobs, self.jobs_path)

        with patch("scheduler.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = cancel_job("surf_20260419_070000", self.jobs_path)

        assert result is True
        remaining = load_jobs(self.jobs_path)
        assert len(remaining) == 0

    def test_cancel_job_calls_schtasks_delete(self):
        jobs = [{
            "job_id": "surf_20260419_070000",
            "task_name": "LetsGoSurf_surf_20260419_070000",
        }]
        save_jobs(jobs, self.jobs_path)

        with patch("scheduler.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            cancel_job("surf_20260419_070000", self.jobs_path)

        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "schtasks"
        assert "/delete" in call_args
        assert "LetsGoSurf_surf_20260419_070000" in call_args

    def test_cancel_nonexistent_job_returns_false(self):
        with patch("scheduler.subprocess.run") as mock_run:
            result = cancel_job("nonexistent_id", self.jobs_path)
        assert result is False
        mock_run.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scheduler.py::TestJobCrud -v`
Expected: FAIL with `ImportError: cannot import name 'load_jobs'`

- [ ] **Step 3: Implement job CRUD functions in `scheduler.py`**

Add after `_parse_time()`:

```python
def load_jobs(jobs_path: str = None) -> list:
    """Load scheduled jobs from JSON file."""
    path = jobs_path or JOBS_PATH
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []


def save_jobs(jobs: list, jobs_path: str = None):
    """Save scheduled jobs to JSON file."""
    path = jobs_path or JOBS_PATH
    with open(path, "w") as f:
        json.dump(jobs, f, indent=2)


def schedule_job(scheduled_time: datetime, location: str, wave_range: str,
                 radius_miles: int, region: str, contact_name: str,
                 send_method: str, jobs_path: str = None) -> dict:
    """Create a scheduled job and register it with Windows Task Scheduler.

    Returns the job dict on success. Raises on schtasks failure or duplicate job_id.
    """
    path = jobs_path or JOBS_PATH
    job_id = f"surf_{scheduled_time.strftime('%Y%m%d_%H%M%S')}"
    task_name = f"LetsGoSurf_{job_id}"

    # Reject duplicate job_id
    existing = load_jobs(path)
    if any(j["job_id"] == job_id for j in existing):
        raise ValueError(f"Job '{job_id}' already exists. Choose a different time.")

    job = {
        "job_id": job_id,
        "created_at": datetime.now().isoformat(),
        "scheduled_time": scheduled_time.isoformat(),
        "location": location,
        "wave_range": wave_range,
        "radius_miles": radius_miles,
        "region": region,
        "contact_name": contact_name,
        "send_method": send_method,
        "task_name": task_name,
    }

    # Register with Windows Task Scheduler
    script_path = os.path.join(APP_DIR, "surf_finder.py")
    command = f'"{sys.executable}" "{script_path}" --run-scheduled {job_id}'

    subprocess.run([
        "schtasks", "/create",
        "/tn", task_name,
        "/tr", command,
        "/sc", "once",
        "/st", scheduled_time.strftime("%H:%M"),
        "/sd", scheduled_time.strftime("%m/%d/%Y"),
        "/f",
    ], check=True, capture_output=True)

    # Persist job
    jobs = load_jobs(path)
    jobs.append(job)
    save_jobs(jobs, path)

    return job


def cancel_job(job_id: str, jobs_path: str = None) -> bool:
    """Cancel a scheduled job. Returns True if found and cancelled, False if not found."""
    path = jobs_path or JOBS_PATH
    jobs = load_jobs(path)

    job = next((j for j in jobs if j["job_id"] == job_id), None)
    if not job:
        return False

    # Remove from Windows Task Scheduler
    try:
        subprocess.run([
            "schtasks", "/delete",
            "/tn", job["task_name"],
            "/f",
        ], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        pass  # Task may already be gone

    # Remove from jobs file
    jobs = [j for j in jobs if j["job_id"] != job_id]
    save_jobs(jobs, path)

    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scheduler.py -v`
Expected: All tests PASS (both TestParseScheduleTime and TestJobCrud)

- [ ] **Step 5: Commit**

```bash
git add scheduler.py tests/test_scheduler.py
git commit -m "feat: add job CRUD with Windows Task Scheduler integration

schedule_job creates a one-time schtasks entry and persists the job.
cancel_job removes both the schtasks entry and the persisted job."
```

---

### Task 5: Implement `run_scheduled_job()` (Headless Execution)

**Files:**
- Modify: `scheduler.py`
- Modify: `tests/test_scheduler.py`

This is the core of the feature — the code path that runs at 7am Sunday with no human interaction.

- [ ] **Step 1: Write the failing tests for `run_scheduled_job`**

Append to `tests/test_scheduler.py`:

```python
from scheduler import run_scheduled_job


def _make_job():
    return {
        "job_id": "surf_20260419_070000",
        "scheduled_time": "2026-04-19T07:00:00",
        "location": "92704",
        "wave_range": "2-3",
        "radius_miles": 30,
        "region": "socal",
        "contact_name": "Brian",
        "send_method": "3",
        "task_name": "LetsGoSurf_surf_20260419_070000",
    }


def _make_config():
    return {
        "gmail_address": "me@gmail.com",
        "gmail_app_password": "xxxx",
        "default_radius_miles": 30,
    }


def _make_contact():
    return {
        "name": "Brian",
        "phone": "9495551234",
        "carrier": "tmobile",
        "device": "iphone",
        "email": "brian@gmail.com",
    }


def _make_conditions():
    return {
        "wave_min": 2, "wave_max": 3,
        "condition_rating": "Fair to Good", "condition_rank": 5,
        "tide_trend": "Rising", "wind_direction_type": "Offshore",
        "wave_human": "", "wind_speed": 5,
    }


class TestRunScheduledJob:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.jobs_path = os.path.join(self.tmpdir, "scheduled_jobs.json")
        self.log_path = os.path.join(self.tmpdir, "scheduled_log.txt")

    def test_successful_run_sends_to_contact_and_self(self):
        job = _make_job()
        save_jobs([job], self.jobs_path)

        spots = [{"name": "Trestles", "lat": 33.38, "lon": -117.59,
                  "surfline_id": "abc", "parking_cost": "Free",
                  "parking_lat": 33.38, "parking_lon": -117.59}]

        with patch("scheduler.load_config", return_value=_make_config()), \
             patch("scheduler.load_contacts", return_value=[_make_contact()]), \
             patch("scheduler.load_region", return_value=spots), \
             patch("scheduler.geocode", return_value=(33.7, -117.9, "Santa Ana, CA")), \
             patch("scheduler.fetch_matching_spots", return_value=[
                 (spots[0], _make_conditions(), 12.3),
             ]), \
             patch("scheduler.send_email", return_value=True) as mock_email, \
             patch("scheduler.send_sms", return_value=True) as mock_sms, \
             patch("scheduler.subprocess.run") as mock_run, \
             patch("scheduler.LOG_PATH", self.log_path):
            mock_run.return_value = MagicMock(returncode=0)

            run_scheduled_job("surf_20260419_070000", self.jobs_path)

        # SMS sent to Brian
        assert mock_sms.call_count == 1
        # Email sent to Brian AND to self
        assert mock_email.call_count == 2
        email_recipients = [call.args[2] for call in mock_email.call_args_list]
        assert "brian@gmail.com" in email_recipients
        assert "me@gmail.com" in email_recipients

        # Job cleaned up
        remaining = load_jobs(self.jobs_path)
        assert len(remaining) == 0

        # Log written
        assert os.path.exists(self.log_path)

    def test_missing_job_id_exits_silently(self):
        save_jobs([], self.jobs_path)

        with patch("scheduler.load_config", return_value=_make_config()):
            # Should not raise
            run_scheduled_job("nonexistent_id", self.jobs_path)

    def test_missing_contact_sends_error_to_self(self):
        job = _make_job()
        save_jobs([job], self.jobs_path)

        with patch("scheduler.load_config", return_value=_make_config()), \
             patch("scheduler.load_contacts", return_value=[]), \
             patch("scheduler.send_email", return_value=True) as mock_email, \
             patch("scheduler.subprocess.run") as mock_run, \
             patch("scheduler.LOG_PATH", self.log_path):
            mock_run.return_value = MagicMock(returncode=0)

            run_scheduled_job("surf_20260419_070000", self.jobs_path)

        # Error email sent to self
        assert mock_email.call_count == 1
        assert "me@gmail.com" in mock_email.call_args.args[2]

    def test_api_failure_sends_error_message(self):
        job = _make_job()
        save_jobs([job], self.jobs_path)

        spots = [{"name": "Trestles", "lat": 33.38, "lon": -117.59,
                  "surfline_id": "abc", "parking_cost": "Free",
                  "parking_lat": 33.38, "parking_lon": -117.59}]

        with patch("scheduler.load_config", return_value=_make_config()), \
             patch("scheduler.load_contacts", return_value=[_make_contact()]), \
             patch("scheduler.load_region", return_value=spots), \
             patch("scheduler.geocode", return_value=(33.7, -117.9, "Santa Ana, CA")), \
             patch("scheduler.fetch_matching_spots", return_value=[]), \
             patch("scheduler.send_email", return_value=True) as mock_email, \
             patch("scheduler.send_sms", return_value=True) as mock_sms, \
             patch("scheduler.subprocess.run") as mock_run, \
             patch("scheduler.time.sleep"), \
             patch("scheduler.LOG_PATH", self.log_path):
            mock_run.return_value = MagicMock(returncode=0)

            run_scheduled_job("surf_20260419_070000", self.jobs_path)

        # Should still send a message (error notice) to contact and self
        assert mock_sms.call_count >= 1 or mock_email.call_count >= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_scheduler.py::TestRunScheduledJob -v`
Expected: FAIL with `ImportError: cannot import name 'run_scheduled_job'`

- [ ] **Step 3: Implement `run_scheduled_job` in `scheduler.py`**

Add the necessary imports at the top of `scheduler.py`:

```python
from config_manager import load_config
from contacts_manager import load_contacts, get_sms_address
from regions_manager import load_region
from geo import geocode
from surf_finder import fetch_matching_spots, build_full_list_message, parse_wave_range
from messaging import send_email, send_sms
```

Add the function after `cancel_job()`:

```python
def _log_result(message: str, log_path: str = None):
    """Append a log line to the scheduled log file."""
    path = log_path or LOG_PATH
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a") as f:
        f.write(f"{timestamp} | {message}\n")


def run_scheduled_job(job_id: str, jobs_path: str = None):
    """Execute a scheduled surf check. Fetches live conditions and sends results.

    This runs non-interactively (called by Windows Task Scheduler).
    """
    path = jobs_path or JOBS_PATH
    config = load_config(os.path.join(APP_DIR, "config.json"))
    gmail = config.get("gmail_address", "")
    gmail_pw = config.get("gmail_app_password", "")

    # Load and find the job
    jobs = load_jobs(path)
    job = next((j for j in jobs if j["job_id"] == job_id), None)
    if not job:
        return  # Already ran or was cancelled

    # Look up contact
    contacts = load_contacts(os.path.join(APP_DIR, "contacts.json"))
    contact = next((c for c in contacts if c["name"] == job["contact_name"]), None)

    if not contact:
        _log_result(f"{job_id} | Contact '{job['contact_name']}' not found | ERROR")
        if gmail and gmail_pw:
            send_email(gmail, gmail_pw, gmail,
                       f"LetsGoSurf: Scheduled check failed",
                       f"Contact '{job['contact_name']}' not found in contacts. "
                       f"Job: {job_id}, scheduled for {job['scheduled_time']}")
        _cleanup_job(job_id, job.get("task_name", ""), path)
        return

    # Load spots and geocode
    region_path = os.path.join(APP_DIR, "spots", f"{job['region']}.json")
    spots = load_region(region_path)
    geo_result = geocode(job["location"])

    if not geo_result:
        _log_result(f"{job_id} | Could not geocode '{job['location']}' | ERROR")
        _send_error_to_all(gmail, gmail_pw, contact, job,
                           f"Could not geocode location '{job['location']}'")
        _cleanup_job(job_id, job.get("task_name", ""), path)
        return

    user_lat, user_lon, location_name = geo_result
    wave_range = parse_wave_range(job["wave_range"])

    # Fetch conditions
    results = fetch_matching_spots(spots, user_lat, user_lon,
                                   job["radius_miles"], wave_range)

    # Retry once if no results (API may be temporarily down)
    if not results:
        time.sleep(60)
        results = fetch_matching_spots(spots, user_lat, user_lon,
                                       job["radius_miles"], wave_range)

    if not results:
        # Send "no conditions available" message
        subject = f"LetsGoSurf: No conditions available near {location_name}"
        body = (f"Scheduled surf check for {job['wave_range']}ft waves "
                f"near {location_name} could not fetch conditions.\n\n"
                f"Surfline may be down. Check manually at surfline.com")
        _send_to_contact(gmail, gmail_pw, contact, job["send_method"], subject, body)
        send_email(gmail, gmail_pw, gmail, subject, body)
        _log_result(f"{job_id} | No conditions available, sent notice | ERROR")
        _cleanup_job(job_id, job.get("task_name", ""), path)
        return

    # Build and send the surf report
    device = contact.get("device", "android")
    subject, body = build_full_list_message(results, location_name, device)

    sent = _send_to_contact(gmail, gmail_pw, contact, job["send_method"], subject, body)
    self_sent = send_email(gmail, gmail_pw, gmail, f"[Copy] {subject}", body)

    if not sent and not self_sent:
        # Gmail auth likely failed — do NOT delete job so user can investigate and retry
        _log_result(f"{job_id} | Send failed (Gmail auth?) — job kept for retry | ERROR")
        return

    _log_result(f"{job_id} | Sent {len(results)} spots to {contact['name']} | OK")
    _cleanup_job(job_id, job.get("task_name", ""), path)


def _send_to_contact(gmail: str, gmail_pw: str, contact: dict,
                     send_method: str, subject: str, body: str) -> bool:
    """Send a message to a contact via their preferred method. Returns True if any send succeeded."""
    sent = False
    can_sms = bool(contact.get("phone") and contact.get("carrier"))
    can_email = bool(contact.get("email"))

    if send_method in ("1", "3") and can_sms:
        sms_addr = get_sms_address(contact["phone"], contact["carrier"])
        if send_sms(gmail, gmail_pw, sms_addr, body):
            sent = True

    if send_method in ("2", "3") and can_email:
        if send_email(gmail, gmail_pw, contact["email"], subject, body):
            sent = True

    return sent


def _send_error_to_all(gmail: str, gmail_pw: str, contact: dict,
                       job: dict, error_msg: str):
    """Send an error notification to both the contact and self."""
    subject = "LetsGoSurf: Scheduled check failed"
    body = f"Your scheduled surf check failed.\n\nError: {error_msg}\n\nJob: {job['job_id']}"
    _send_to_contact(gmail, gmail_pw, contact, job["send_method"], subject, body)
    send_email(gmail, gmail_pw, gmail, subject, body)


def _cleanup_job(job_id: str, task_name: str, jobs_path: str):
    """Remove job from JSON and delete the Windows Scheduled Task."""
    # Remove from jobs file
    jobs = load_jobs(jobs_path)
    jobs = [j for j in jobs if j["job_id"] != job_id]
    save_jobs(jobs, jobs_path)

    # Remove from Task Scheduler
    if task_name:
        try:
            subprocess.run([
                "schtasks", "/delete", "/tn", task_name, "/f",
            ], capture_output=True, check=False)
        except Exception:
            pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_scheduler.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add scheduler.py tests/test_scheduler.py
git commit -m "feat: add run_scheduled_job for headless execution

Fetches live conditions at scheduled time, sends results to contact
and a copy to self. Handles API failures with retry, missing contacts
with error notification, and cleans up after execution."
```

---

### Task 6: Add "Scheduled Checks" Submenu to `surf_finder.py`

**Files:**
- Modify: `surf_finder.py`

This task wires up the interactive scheduling flow in the main menu.

- [ ] **Step 1: Add the import for scheduler functions**

At the top of `surf_finder.py`, add:

```python
from scheduler import (
    parse_schedule_time, schedule_job, cancel_job,
    load_jobs, run_scheduled_job,
)
```

- [ ] **Step 2: Add the `scheduled_checks_menu` function**

Add before `main()`:

```python
def scheduled_checks_menu(config: dict, contacts: list) -> list:
    """Interactive submenu for managing scheduled surf checks."""
    while True:
        print("\n  Scheduled Checks:")
        print("    1) Schedule a new check")
        print("    2) View upcoming checks")
        print("    3) Cancel a check")
        print("    4) Back")

        choice = input("\n  Choice: ").strip()

        if choice == "1":
            contacts = schedule_new_check(config, contacts)
        elif choice == "2":
            view_upcoming_checks()
        elif choice == "3":
            cancel_check()
        elif choice == "4":
            break
        else:
            print("  Invalid choice. Enter 1-4.")

    return contacts


def schedule_new_check(config: dict, contacts: list) -> list:
    """Interactive flow to schedule a new surf check."""
    # Select region
    regions = list_regions(SPOTS_DIR)
    if not regions:
        print("\n  No spot regions found. Add one in 'Manage spot regions' first.")
        return contacts

    if len(regions) == 1:
        region_name, region_count, region_path = regions[0]
        print(f"\n  Using region: {region_name.title()} ({region_count} spots)")
    else:
        print("\n  Select region:")
        for i, (name, count, _) in enumerate(regions):
            print(f"    {i + 1}) {name.title()} ({count} spots)")
        try:
            idx = int(input("\n  Region #: ").strip()) - 1
            region_name, region_count, region_path = regions[idx]
        except (ValueError, IndexError):
            print("  Invalid choice.")
            return contacts

    # Location
    home = config.get("home_location", "")
    if home:
        loc_input = input(f"\n  Location [{home}]: ").strip()
        if not loc_input:
            loc_input = home
    else:
        loc_input = input("\n  Enter your location (zip or city): ").strip()

    # Validate location
    print("  Geocoding...")
    geo_result = geocode(loc_input)
    if not geo_result:
        print("  Could not find that location. Try a zip code or different city name.")
        return contacts
    _, _, location_display = geo_result
    print(f"  Found: {location_display}")

    # Wave size
    wave_input = input("  Desired wave size (e.g., 2-3): ").strip()
    wave_range = parse_wave_range(wave_input)
    if not wave_range:
        print("  Invalid format. Use min-max like '2-3' or '3-4'.")
        return contacts

    # When to check
    print("\n  When should we check?")
    print("  Examples: 'Sunday 7am', 'tomorrow 6:30pm', '2026-04-19 07:00'")
    time_input = input("  When: ").strip()
    scheduled_time = parse_schedule_time(time_input)
    if not scheduled_time:
        print("  Invalid or past time. Try again.")
        return contacts

    display_time = scheduled_time.strftime("%A, %B %d, %Y at %I:%M %p")
    print(f"  Scheduled for: {display_time}")

    # Select contact
    if not contacts:
        print("\n  No contacts saved. Add one in 'Manage contacts' first.")
        return contacts

    print("\n  Send to:")
    for i, c in enumerate(contacts):
        print(f"    {i + 1}) {c['name']} — {display_contact(c)}")
    print(f"    {len(contacts) + 1}) Enter new recipient")

    try:
        recip_choice = int(input("\n  Choice: ").strip()) - 1
    except ValueError:
        print("  Invalid choice.")
        return contacts

    is_new = recip_choice == len(contacts)
    if is_new:
        contact = prompt_new_contact()
    elif 0 <= recip_choice < len(contacts):
        contact = contacts[recip_choice]
    else:
        print("  Invalid choice.")
        return contacts

    # Send method
    can_sms = bool(contact.get("phone") and contact.get("carrier"))
    can_email = bool(contact.get("email"))

    if can_sms and can_email:
        print("\n  How to send?")
        print("    1) Text (SMS)")
        print("    2) Email")
        print("    3) Both")
        method = input("  Choice: ").strip()
        if method not in ("1", "2", "3"):
            print("  Invalid choice.")
            return contacts
    elif can_sms:
        method = "1"
    elif can_email:
        method = "2"
    else:
        print("  Contact has no phone or email.")
        return contacts

    # Schedule it
    radius = config.get("default_radius_miles", 30)

    try:
        job = schedule_job(
            scheduled_time=scheduled_time,
            location=loc_input,
            wave_range=wave_input,
            radius_miles=radius,
            region=region_name,
            contact_name=contact["name"],
            send_method=method,
        )
    except Exception as e:
        print(f"\n  Failed to create scheduled task: {e}")
        print("  You may need to run as administrator.")
        return contacts

    method_name = {"1": "text", "2": "email", "3": "text & email"}.get(method, "message")
    short_time = scheduled_time.strftime("%a %b %d %I:%M %p")
    gmail = config.get("gmail_address", "")
    print(f"\n  Scheduled! Surf check will run at {short_time}")
    print(f"    Results sent to {contact['name']} via {method_name}")
    print(f"    A copy will also be sent to you ({gmail})")

    # Save new contact if needed
    if is_new:
        if input("\n  Save this contact for next time? (y/n): ").strip().lower() == "y":
            name = input("    Name: ").strip()
            if name:
                contact["name"] = name
            contacts = add_contact(contacts, contact)
            save_contacts(contacts, CONTACTS_PATH)
            print(f"    Saved \"{contact['name']}\"!")

    return contacts


def view_upcoming_checks():
    """Display all pending scheduled checks."""
    jobs = load_jobs()
    if not jobs:
        print("\n  No scheduled checks.")
        return

    print(f"\n  {'#':<4}{'When':<26}{'Location':<12}{'Waves':<10}{'Contact':<12}Send via")
    print("  " + "-" * 74)
    for i, job in enumerate(jobs):
        dt = datetime.fromisoformat(job["scheduled_time"])
        when = dt.strftime("%a %b %d, %I:%M %p")
        method_name = {"1": "text", "2": "email", "3": "text & email"}.get(
            job["send_method"], "?")
        waves = f"{job['wave_range']}ft"
        print(f"  {i+1:<4}{when:<26}{job['location']:<12}{waves:<10}"
              f"{job['contact_name']:<12}{method_name}")


def cancel_check():
    """Interactive flow to cancel a scheduled check."""
    jobs = load_jobs()
    if not jobs:
        print("\n  No scheduled checks to cancel.")
        return

    view_upcoming_checks()

    try:
        idx = int(input("\n  Cancel check #: ").strip()) - 1
        if not (0 <= idx < len(jobs)):
            print("  Invalid choice.")
            return
    except ValueError:
        print("  Invalid choice.")
        return

    job = jobs[idx]
    if cancel_job(job["job_id"]):
        print(f"  Cancelled: {job['job_id']}")
    else:
        print("  Failed to cancel. Job may have already run.")
```

- [ ] **Step 3: Add the `datetime` import**

At the top of `surf_finder.py`, add:

```python
from datetime import datetime
```

- [ ] **Step 4: Update `main()` menu**

Replace the `main()` function's menu loop:

```python
def main():
    # Handle --run-scheduled CLI flag
    if len(sys.argv) == 3 and sys.argv[1] == "--run-scheduled":
        run_scheduled_job(sys.argv[2])
        return

    print("\n  LetsGoSurf - Surf Finder\n")

    config = load_config(CONFIG_PATH)
    if not config.get("gmail_address"):
        print("  Welcome! Let's get you set up.\n")
        config = first_run_setup(CONFIG_PATH)

    contacts = load_contacts(CONTACTS_PATH)

    while True:
        print("\n  Main Menu:")
        print("    1) Find waves now")
        print("    2) Manage spot regions")
        print("    3) Manage contacts")
        print("    4) Settings")
        print("    5) Scheduled checks")
        print("    6) Quit")

        choice = input("\n  Choice: ").strip()
        if choice == "1":
            contacts = find_waves(config, contacts)
        elif choice == "2":
            regions_menu(SPOTS_DIR)
        elif choice == "3":
            contacts = contacts_menu(contacts, CONTACTS_PATH)
        elif choice == "4":
            config = settings_menu(config, CONFIG_PATH)
        elif choice == "5":
            contacts = scheduled_checks_menu(config, contacts)
        elif choice == "6":
            print("\n  Hang loose!\n")
            break
        else:
            print("  Invalid choice. Enter 1-6.")
```

- [ ] **Step 5: Run the full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add surf_finder.py
git commit -m "feat: add scheduled checks menu and CLI entry point

New menu option 5 for scheduling, viewing, and cancelling surf checks.
--run-scheduled flag enables headless execution by Windows Task Scheduler."
```

---

### Task 7: Add `.gitignore` Entries for Runtime Files

**Files:**
- Modify: `.gitignore` (create if doesn't exist)

- [ ] **Step 1: Check if `.gitignore` exists**

Run: `ls -la .gitignore`

- [ ] **Step 2: Add runtime file entries**

Add these lines to `.gitignore` (create the file if it doesn't exist):

```
# Runtime data (user-specific, not committed)
config.json
contacts.json
scheduled_jobs.json
scheduled_log.txt

# Python
__pycache__/
*.pyc
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: add gitignore for runtime data and Python cache"
```

---

### Task 8: End-to-End Manual Test

**Files:** None (verification only)

- [ ] **Step 1: Run the full test suite one final time**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run the app and test the scheduling flow**

Run: `python surf_finder.py`

Walk through:
1. Main menu → 5 (Scheduled checks)
2. Schedule a new check → pick region, enter location, wave size, time "tomorrow 7am", pick contact, pick send method
3. Verify confirmation message shows correct details
4. View upcoming checks → verify the job appears
5. Cancel the check → verify it's removed
6. View upcoming checks → verify empty

- [ ] **Step 3: Verify Windows Task Scheduler integration**

Run: `schtasks /query /fo csv /nh | findstr LetsGoSurf`
Expected: No tasks (we just cancelled it)

Schedule another check, then verify:
Run: `schtasks /query /fo csv /nh | findstr LetsGoSurf`
Expected: One task with the correct name and time

Clean up: cancel the test check from the app.

- [ ] **Step 4: Commit any final adjustments**

If any issues were found and fixed during manual testing, commit them:

```bash
git add -A
git commit -m "fix: adjustments from end-to-end testing"
```
