from datetime import datetime
from unittest.mock import patch
from scheduler import parse_schedule_time


def _mock_now(year, month, day, hour=12, minute=0):
    """Return a patcher that fixes _get_now() to a specific time."""
    fixed = datetime(year, month, day, hour, minute, 0)
    return patch("scheduler._get_now", return_value=fixed)


class TestParseScheduleTime:
    def test_explicit_datetime(self):
        with _mock_now(2026, 4, 9, 20, 0):
            result = parse_schedule_time("2026-04-19 07:00")
        assert result == datetime(2026, 4, 19, 7, 0)

    def test_day_name_and_time_am(self):
        # Thursday Apr 9 2026 at 8pm -> "Sunday 7am" = Apr 12 2026 07:00
        with _mock_now(2026, 4, 9, 20, 0):
            result = parse_schedule_time("Sunday 7am")
        assert result == datetime(2026, 4, 12, 7, 0)

    def test_day_name_case_insensitive(self):
        with _mock_now(2026, 4, 9, 20, 0):
            result = parse_schedule_time("sunday 7am")
        assert result == datetime(2026, 4, 12, 7, 0)

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

    def test_today_future_time(self):
        # 6am, scheduling "today 8:30am" -> today at 8:30
        with _mock_now(2026, 4, 9, 6, 0):
            result = parse_schedule_time("today 8:30am")
        assert result == datetime(2026, 4, 9, 8, 30)

    def test_today_past_time_returns_none(self):
        # 10am, scheduling "today 8:30am" -> None (past)
        with _mock_now(2026, 4, 9, 10, 0):
            result = parse_schedule_time("today 8:30am")
        assert result is None

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


import os
import json
import tempfile
from unittest.mock import MagicMock
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
        with patch("scheduler.subprocess.run") as mock_run:
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

        saved = load_jobs(self.jobs_path)
        assert len(saved) == 1
        assert saved[0]["job_id"] == "surf_20260419_070000"

    def test_schedule_job_calls_schtasks_create(self):
        with patch("scheduler.subprocess.run") as mock_run:
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

        assert mock_sms.call_count >= 1 or mock_email.call_count >= 1
