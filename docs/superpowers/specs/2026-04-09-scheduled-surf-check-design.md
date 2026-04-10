# Scheduled Surf Check — Design Spec

## Overview

Add the ability to schedule a future surf conditions check that runs automatically at a specified date/time, fetches live conditions from Surfline/Open-Meteo, filters spots by wave range and proximity, and sends the results to a contact via SMS and/or email. A copy is also sent to the user.

**Use case:** You know you're going surfing next Sunday morning. A couple nights before, you schedule a check for Sunday 7am, 2-3ft waves near 92704, send to Brian via text and email. At 7am Sunday, your PC runs the check automatically — no interaction needed.

## Architecture Decision

**Windows Task Scheduler via `schtasks.exe`** was chosen over APScheduler, background daemons, or hybrid approaches because:

- Zero external dependencies — `schtasks.exe` ships with every Windows install
- Survives reboots, sleep/wake, and user logoff
- The app itself doesn't need to stay running
- No admin privileges required for per-user tasks
- One-time scheduled tasks (`/sc once`) are a perfect fit

## Data Model

### `scheduled_jobs.json`

Created on first schedule. Stores pending jobs as a JSON array:

```json
[
  {
    "job_id": "surf_20260419_070000",
    "created_at": "2026-04-09T22:15:00",
    "scheduled_time": "2026-04-19T07:00:00",
    "location": "92704",
    "wave_range": "2-3",
    "radius_miles": 30,
    "region": "socal",
    "contact_name": "Brian",
    "send_method": "3",
    "task_name": "LetsGoSurf_surf_20260419_070000"
  }
]
```

Field details:

- `job_id` — derived from scheduled time: `surf_YYYYMMDD_HHMMSS`. Simple, readable, unique for a single-user app.
- `contact_name` — references contact by name in `contacts.json`. Looked up at execution time so contact detail changes are reflected.
- `send_method` — "1" (SMS), "2" (email), or "3" (both). Same codes as existing flow.
- `task_name` — Windows Task Scheduler task name, prefixed with `LetsGoSurf_`. Stored for cancellation.
- `region` — region key (e.g., "socal") so the correct spots file is loaded at runtime.
- `radius_miles` — captured from config at schedule time.

The job does **not** store spot lists or conditions — those are fetched live at the scheduled time.

### `scheduled_log.txt`

Appended after each scheduled run. One line per execution:

```
2026-04-19 07:01:23 | surf_20260419_070000 | Sent 5 spots to Brian via text & email | OK
2026-04-19 07:01:23 | surf_20260419_070000 | API failure, sent error notice to self | ERROR
```

## Interactive Flow

### Menu Changes

Main menu adds option 5 "Scheduled checks", renumbers Quit to 6:

```
Main Menu:
  1) Find waves now
  2) Manage spot regions
  3) Manage contacts
  4) Settings
  5) Scheduled checks
  6) Quit
```

### Scheduled Checks Submenu

```
Scheduled Checks:
  1) Schedule a new check
  2) View upcoming checks
  3) Cancel a check
  4) Back
```

### Schedule a New Check Flow

1. Select region (reuses existing region selection)
2. Enter location (zip or city, with home default)
3. Enter desired wave size (e.g., "2-3")
4. Enter when to check — accepts:
   - Day + time: "Sunday 7am", "saturday 6:30pm", "tomorrow 6am" (day names: monday-sunday, plus "tomorrow")
   - Explicit: "2026-04-19 07:00"
   - Validates the time is in the future
   - "tomorrow" resolves to the next calendar day; day names resolve to the next occurrence (today if time hasn't passed, otherwise next week)
5. Select contact (reuses existing contact selection)
6. Select send method: SMS, email, or both (reuses existing flow)
7. Confirmation message showing scheduled time, recipient, and method

### View Upcoming Checks

Displays a table of pending jobs:

```
  #  When                    Location  Waves  Contact  Send via
  1  Sun Apr 19, 7:00 AM     92704     2-3ft  Brian    text & email
  2  Sat Apr 25, 6:00 AM     92672     3-4ft  Jake     email
```

### Cancel a Check

Shows upcoming checks, prompts for number to cancel. Removes from `scheduled_jobs.json` and deletes the Windows Scheduled Task.

## Headless Execution

### CLI Entry Point

```
python surf_finder.py --run-scheduled surf_20260419_070000
```

Detected via `sys.argv` in `surf_finder.py` (no `argparse` needed for one flag).

### Execution Steps

1. Load job from `scheduled_jobs.json` by `job_id`
2. Load config (`config.json`) for Gmail credentials
3. Look up contact by name from `contacts.json`
4. Load region spots from `spots/<region>.json`
5. Geocode the stored location
6. Filter spots by radius (same haversine logic as `find_waves()`)
7. Fetch live conditions from Surfline (fallback to Open-Meteo)
8. Filter by wave range:
   - If matches exist: build full list message with all matching spots
   - If no exact matches: send all nearby conditions with a note
9. Send to contact via stored method (SMS, email, or both)
10. Send a copy to self (user's Gmail address)
11. Clean up: remove job from `scheduled_jobs.json`, delete Windows Scheduled Task
12. Log result to `scheduled_log.txt`

### Error Handling

| Scenario | Behavior |
|----------|----------|
| Gmail auth fails | Log error, do NOT delete job (user can investigate and retry) |
| Surfline/Open-Meteo API down | Retry once after 60 seconds. If still down, send message to contact and self: "Couldn't fetch conditions — Surfline may be down" |
| Contact not found in contacts.json | Log error, send notification to self explaining what happened |
| Job ID not found in scheduled_jobs.json | Exit silently (already ran or was cancelled) |
| schtasks delete fails during cleanup | Log warning, continue (non-critical) |

## Windows Task Scheduler Integration

### New Module: `scheduler.py`

All `schtasks.exe` interaction is encapsulated here.

**Create a task:**

```python
subprocess.run([
    "schtasks", "/create",
    "/tn", "LetsGoSurf_surf_20260419_070000",
    "/tr", f'"{sys.executable}" "{script_path}" --run-scheduled surf_20260419_070000',
    "/sc", "once",
    "/st", "07:00",
    "/sd", "04/19/2026",
    "/f"
], check=True)
```

**List tasks (our app's only):**

```python
subprocess.run(["schtasks", "/query", "/fo", "csv", "/nh"], capture_output=True, text=True)
# Filter output for lines containing "LetsGoSurf_"
```

**Delete a task:**

```python
subprocess.run([
    "schtasks", "/delete",
    "/tn", "LetsGoSurf_surf_20260419_070000",
    "/f"
], check=True)
```

Key implementation details:

- `subprocess.run()` with list args (not shell string) — no shell injection risk
- `sys.executable` for Python path — works in any install (system, venv, pyenv)
- No admin privileges required for per-user scheduled tasks
- Task names prefixed with `LetsGoSurf_` to avoid collisions

## Module Structure

### New Files

- `scheduler.py` (~150 lines) — job CRUD, Windows Task Scheduler integration, headless execution, date parsing
- `scheduled_jobs.json` — created on first schedule
- `scheduled_log.txt` — created on first headless run
- `test_scheduler.py` — unit tests

### Modified Files

- `surf_finder.py` — CLI arg handling, new menu option, extracted shared logic

### Extracted Functions (in `surf_finder.py`)

These are pulled out of `find_waves()` so both the interactive and headless paths can use them:

- `fetch_matching_spots(spots, user_lat, user_lon, radius, wave_range)` — filters spots by distance and fetches/filters conditions. Pure logic, no I/O.
- `build_full_list_message(results, location_name, device)` — builds subject and body for a multi-spot message. Pure logic, no I/O.

`find_waves()` calls these after gathering interactive input. `run_scheduled_job()` calls them directly with stored parameters.

### Unchanged Files

- `messaging.py` — `send_email()` and `send_sms()` already do what we need
- `contacts_manager.py` — contact lookup by name is a simple list filter
- `surfline_api.py` / `openmeteo_api.py` — unchanged
- `config_manager.py` — unchanged
- `regions_manager.py` — `load_region()` already takes a path

## Testing

### `test_scheduler.py`

**Date parsing (`parse_schedule_time`):**

- "Sunday 7am" → next upcoming Sunday at 07:00
- "saturday 6:30pm" → case-insensitive, 12-hour time
- "2026-04-19 07:00" → explicit datetime
- Past times rejected
- Day-only or time-only input rejected
- Edge: "Sunday 7am" on Sunday before 7am → today
- Edge: "Sunday 7am" on Sunday after 7am → next Sunday

**Job scheduling (`schedule_job`):**

- Job written to JSON with all required fields
- `schtasks /create` called with correct arguments (mock `subprocess.run`)
- Duplicate `job_id` rejected

**Job cancellation (`cancel_job`):**

- Job removed from JSON
- `schtasks /delete` called with correct task name (mock `subprocess.run`)
- Nonexistent `job_id` handled gracefully

**Headless execution (`run_scheduled_job`):**

- End-to-end with mocked APIs and messaging: loads job, fetches conditions, sends to contact AND self
- Job cleaned up from JSON after success
- API failure: retries once, then sends error notification
- Missing contact: sends error to self
- Missing job_id: exits without error

### Existing Test Updates

- Test `fetch_matching_spots()` and `build_full_list_message()` as extracted pure functions
