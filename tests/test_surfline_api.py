from unittest.mock import patch, MagicMock
from surfline_api import get_surfline_conditions


def _mock_surfline_responses():
    """Return mock responses for wave, wind, tides, conditions endpoints."""
    wave_resp = MagicMock()
    wave_resp.status_code = 200
    wave_resp.json.return_value = {
        "data": {
            "wave": [{
                "timestamp": 1700000000,
                "surf": {"min": 2, "max": 3, "humanRelation": "Waist to chest"},
                "swells": [{"height": 3.5, "period": 12, "direction": 200}],
            }]
        }
    }

    wind_resp = MagicMock()
    wind_resp.status_code = 200
    wind_resp.json.return_value = {
        "data": {
            "wind": [{
                "timestamp": 1700000000,
                "speed": 5,
                "direction": 315,
                "directionType": "Offshore",
            }]
        }
    }

    tides_resp = MagicMock()
    tides_resp.status_code = 200
    tides_resp.json.return_value = {
        "data": {
            "tides": [
                {"timestamp": 1699990000, "height": 2.0, "type": "NORMAL"},
                {"timestamp": 1700000000, "height": 3.0, "type": "NORMAL"},
                {"timestamp": 1700010000, "height": 4.0, "type": "HIGH"},
            ]
        }
    }

    conditions_resp = MagicMock()
    conditions_resp.status_code = 200
    conditions_resp.json.return_value = {
        "data": {
            "conditions": [{
                "timestamp": 1700000000,
                "am": {"rating": "FAIR_TO_GOOD", "humanRelation": "Fair to Good"},
                "pm": {"rating": "FAIR", "humanRelation": "Fair"},
            }]
        }
    }

    return [wave_resp, wind_resp, tides_resp, conditions_resp]


def test_get_surfline_conditions_success():
    with patch("surfline_api.requests.get", side_effect=_mock_surfline_responses()):
        result = get_surfline_conditions("5842041f4e65fad6a7708890")
        assert result is not None
        assert result["wave_min"] == 2
        assert result["wave_max"] == 3
        assert result["wind_direction_type"] == "Offshore"
        assert result["condition_rating"] in ("Fair to Good", "Fair")


def test_get_surfline_conditions_api_failure():
    fail_resp = MagicMock()
    fail_resp.status_code = 500
    fail_resp.raise_for_status.side_effect = Exception("Server error")

    with patch("surfline_api.requests.get", return_value=fail_resp):
        result = get_surfline_conditions("bad_id")
        assert result is None
