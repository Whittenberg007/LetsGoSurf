import requests

METERS_TO_FEET = 3.28084


def get_openmeteo_conditions(lat: float, lon: float) -> dict | None:
    """Fetch current wave conditions from Open-Meteo. Returns None on failure.
    Used as fallback for spots without a Surfline ID (international spots)."""
    try:
        resp = requests.get(
            "https://marine-api.open-meteo.com/v1/marine",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "wave_height,wave_direction,wave_period",
            },
            timeout=10,
        )
        current = resp.json()["current"]
        wave_height_ft = current["wave_height"] * METERS_TO_FEET
        # Open-ocean data gives a single height — use a +/- 0.3ft range
        wave_min = round(wave_height_ft - 0.3, 1)
        wave_max = round(wave_height_ft + 0.3, 1)
        if wave_min < 0:
            wave_min = 0

        return {
            "wave_min": wave_min,
            "wave_max": wave_max,
            "wave_human": f"{wave_min}-{wave_max} ft (ocean model)",
            "wind_speed": 0,
            "wind_direction_type": "Unknown",
            "tide_trend": "Unknown",
            "condition_rating": "N/A (open-ocean data)",
            "condition_rank": 4,  # default to FAIR rank for sorting
        }
    except Exception:
        return None
