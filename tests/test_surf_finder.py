from unittest.mock import patch
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
