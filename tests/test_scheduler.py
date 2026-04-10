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
