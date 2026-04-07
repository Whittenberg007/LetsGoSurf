from unittest.mock import patch, MagicMock
from openmeteo_api import get_openmeteo_conditions


def test_openmeteo_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "current": {
            "wave_height": 1.2,
            "wave_direction": 200,
            "wave_period": 12,
        }
    }
    with patch("openmeteo_api.requests.get", return_value=mock_resp):
        result = get_openmeteo_conditions(33.38, -117.59)
        assert result is not None
        # Open-Meteo gives meters; 1.2m ~ 3.9ft
        assert 3.5 < result["wave_min"] < 4.5
        assert result["condition_rating"] == "N/A (open-ocean data)"


def test_openmeteo_failure():
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.raise_for_status.side_effect = Exception("fail")
    mock_resp.json.side_effect = Exception("fail")
    with patch("openmeteo_api.requests.get", return_value=mock_resp):
        result = get_openmeteo_conditions(33.38, -117.59)
        assert result is None
