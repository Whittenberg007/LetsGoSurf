from geo import haversine_miles
from unittest.mock import patch, MagicMock
from geo import geocode


def test_haversine_same_point():
    assert haversine_miles(33.0, -117.0, 33.0, -117.0) == 0.0


def test_haversine_known_distance():
    # San Clemente (33.4270, -117.6120) to Huntington Beach (33.6603, -117.9992)
    # Known distance ~28 miles
    dist = haversine_miles(33.4270, -117.6120, 33.6603, -117.9992)
    assert 27.0 < dist < 30.0


def test_haversine_short_distance():
    # Trestles to T-Street, roughly 3-4 miles
    dist = haversine_miles(33.3822, -117.5893, 33.4175, -117.6230)
    assert 2.0 < dist < 5.0


def test_geocode_census_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": {
            "addressMatches": [{
                "coordinates": {"x": -117.612, "y": 33.427}
            }]
        }
    }
    with patch("geo.requests.get", return_value=mock_response) as mock_get:
        lat, lon, name = geocode("92672")
        assert abs(lat - 33.427) < 0.01
        assert abs(lon - (-117.612)) < 0.01


def test_geocode_census_fails_openmeteo_fallback():
    census_response = MagicMock()
    census_response.status_code = 200
    census_response.json.return_value = {"result": {"addressMatches": []}}

    openmeteo_response = MagicMock()
    openmeteo_response.status_code = 200
    openmeteo_response.json.return_value = {
        "results": [{
            "latitude": 33.427,
            "longitude": -117.612,
            "name": "San Clemente"
        }]
    }

    with patch("geo.requests.get", side_effect=[census_response, openmeteo_response]):
        lat, lon, name = geocode("San Clemente")
        assert abs(lat - 33.427) < 0.01
        assert name == "San Clemente"


def test_geocode_both_fail():
    fail_response = MagicMock()
    fail_response.status_code = 200
    fail_response.json.return_value = {"result": {"addressMatches": []}}

    fail_response2 = MagicMock()
    fail_response2.status_code = 200
    fail_response2.json.return_value = {"results": []}

    with patch("geo.requests.get", side_effect=[fail_response, fail_response2]):
        result = geocode("xyznonexistent")
        assert result is None
