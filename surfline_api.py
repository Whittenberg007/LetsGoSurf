import time
import requests

BASE_URL = "https://services.surfline.com/kbyg/spots/forecasts"

CONDITION_RANK = {
    "FLAT": 0,
    "VERY_POOR": 1,
    "POOR": 2,
    "POOR_TO_FAIR": 3,
    "FAIR": 4,
    "FAIR_TO_GOOD": 5,
    "GOOD": 6,
    "GOOD_TO_EPIC": 7,
    "EPIC": 8,
}


def _get_current_entry(entries: list, timestamp_key: str = "timestamp"):
    """Find the forecast entry closest to the current time."""
    now = time.time()
    closest = None
    closest_diff = float("inf")
    for entry in entries:
        diff = abs(entry[timestamp_key] - now)
        if diff < closest_diff:
            closest_diff = diff
            closest = entry
    return closest


def _get_tide_trend(tides: list) -> str:
    """Determine if tide is rising or falling based on nearby entries."""
    now = time.time()
    before = None
    after = None
    for t in tides:
        if t["timestamp"] <= now:
            before = t
        elif after is None:
            after = t
    if before and after:
        return "Rising" if after["height"] > before["height"] else "Falling"
    return "Unknown"


def get_surfline_conditions(spot_id: str) -> dict | None:
    """Fetch current conditions for a Surfline spot. Returns None on failure."""
    try:
        params = {"spotId": spot_id, "days": 1}
        wave_resp = requests.get(f"{BASE_URL}/wave", params=params, timeout=10)
        wind_resp = requests.get(f"{BASE_URL}/wind", params=params, timeout=10)
        tides_resp = requests.get(f"{BASE_URL}/tides", params=params, timeout=10)
        cond_resp = requests.get(f"{BASE_URL}/conditions", params=params, timeout=10)

        wave_data = wave_resp.json()["data"]["wave"]
        wind_data = wind_resp.json()["data"]["wind"]
        tides_data = tides_resp.json()["data"]["tides"]
        cond_data = cond_resp.json()["data"]["conditions"]

        wave = _get_current_entry(wave_data)
        wind = _get_current_entry(wind_data)
        cond = cond_data[0]  # conditions are per-day, not per-hour

        # Pick AM or PM rating based on current hour
        hour = time.localtime().tm_hour
        period = cond.get("am") if hour < 12 else cond.get("pm")
        if not period:
            period = cond.get("am") or cond.get("pm") or {}

        rating_key = period.get("rating", "FAIR")
        rating_human = period.get("humanRelation", rating_key.replace("_", " ").title())
        rating_rank = CONDITION_RANK.get(rating_key, 4)

        return {
            "wave_min": wave["surf"]["min"],
            "wave_max": wave["surf"]["max"],
            "wave_human": wave["surf"].get("humanRelation", ""),
            "wind_speed": wind.get("speed", 0),
            "wind_direction_type": wind.get("directionType", "Unknown"),
            "tide_trend": _get_tide_trend(tides_data),
            "condition_rating": rating_human,
            "condition_rank": rating_rank,
        }
    except Exception:
        return None
