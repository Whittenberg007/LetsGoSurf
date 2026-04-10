import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

from config_manager import load_config
from contacts_manager import load_contacts, get_sms_address
from regions_manager import load_region
from geo import geocode
from surf_finder import fetch_matching_spots, build_full_list_message, parse_wave_range
from messaging import send_email, send_sms

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
    if day_str == "today":
        target_date = now.date()
    elif day_str == "tomorrow":
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
    jobs = load_jobs(jobs_path)
    jobs = [j for j in jobs if j["job_id"] != job_id]
    save_jobs(jobs, jobs_path)

    if task_name:
        try:
            subprocess.run([
                "schtasks", "/delete", "/tn", task_name, "/f",
            ], capture_output=True, check=False)
        except Exception:
            pass
