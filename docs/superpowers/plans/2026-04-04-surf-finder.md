# Surf Finder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI app that finds surf spots near you matching your desired wave size, shows live conditions, and can text/email directions to contacts.

**Architecture:** Modular Python app split into focused files — one per responsibility (geo, APIs, messaging, config, contacts, regions). Single entry point (`surf_finder.py`) with main menu. Data files in `spots/` directory, user config in `config.json` and `contacts.json`.

**Tech Stack:** Python 3.10+, `requests` library, Python standard library (`smtplib`, `json`, `math`, `email`). `pytest` for testing.

---

## File Structure

```
C:\Repos\LetsGoSurf\
  surf_finder.py          # Entry point + main menu loop
  geo.py                  # Haversine distance + geocoding (Census + Open-Meteo fallback)
  surfline_api.py         # Surfline unofficial API client (waves, tide, wind, conditions)
  openmeteo_api.py        # Open-Meteo marine wave API fallback
  messaging.py            # Email + SMS sending via Gmail SMTP
  config_manager.py       # Config load/save/first-run setup/settings menu
  contacts_manager.py     # Contact CRUD + contacts menu
  regions_manager.py      # Region/spot CRUD + regions menu
  spots/
    socal.json            # Pre-populated ~50 SoCal surf spots
  tests/
    test_geo.py
    test_surfline_api.py
    test_openmeteo_api.py
    test_messaging.py
    test_config_manager.py
    test_contacts_manager.py
    test_regions_manager.py
  requirements.txt
  .gitignore
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
requests>=2.28.0
pytest>=7.0.0
```

- [ ] **Step 2: Create .gitignore**

```
__pycache__/
*.pyc
config.json
contacts.json
.pytest_cache/
venv/
.env
```

Note: `config.json` and `contacts.json` are gitignored because they contain user credentials and personal contacts.

- [ ] **Step 3: Create empty tests package**

Create `tests/__init__.py` as an empty file.

- [ ] **Step 4: Install dependencies**

Run: `pip install requests pytest`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore tests/__init__.py
git commit -m "chore: project scaffolding with requirements and gitignore"
```

---

### Task 2: Geo Module — Haversine Distance

**Files:**
- Create: `geo.py`
- Create: `tests/test_geo.py`

- [ ] **Step 1: Write failing tests for haversine**

```python
# tests/test_geo.py
from geo import haversine_miles


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_geo.py -v`
Expected: FAIL — `cannot import name 'haversine_miles' from 'geo'`

- [ ] **Step 3: Implement haversine**

```python
# geo.py
import math


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in miles."""
    R = 3956  # Earth's radius in miles
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_geo.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add geo.py tests/test_geo.py
git commit -m "feat: add haversine distance calculation"
```

---

### Task 3: Geo Module — Geocoding

**Files:**
- Modify: `geo.py`
- Modify: `tests/test_geo.py`

- [ ] **Step 1: Write failing tests for geocoding**

Append to `tests/test_geo.py`:

```python
from unittest.mock import patch, MagicMock
from geo import geocode


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_geo.py::test_geocode_census_success -v`
Expected: FAIL — `cannot import name 'geocode' from 'geo'`

- [ ] **Step 3: Implement geocoding**

Append to `geo.py`:

```python
import requests


def geocode(query: str):
    """Convert zip/city to (lat, lon, display_name). Returns None if both services fail."""
    # Try US Census geocoder first
    try:
        resp = requests.get(
            "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress",
            params={"address": query, "benchmark": "Public_AR_Current", "format": "json"},
            timeout=10,
        )
        matches = resp.json().get("result", {}).get("addressMatches", [])
        if matches:
            coords = matches[0]["coordinates"]
            address = matches[0].get("matchedAddress", query)
            return coords["y"], coords["x"], address
    except Exception:
        pass

    # Fallback to Open-Meteo geocoding
    try:
        resp = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": query, "count": 1},
            timeout=10,
        )
        results = resp.json().get("results", [])
        if results:
            r = results[0]
            return r["latitude"], r["longitude"], r.get("name", query)
    except Exception:
        pass

    return None
```

- [ ] **Step 4: Run all geo tests**

Run: `pytest tests/test_geo.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add geo.py tests/test_geo.py
git commit -m "feat: add geocoding with Census primary and Open-Meteo fallback"
```

---

### Task 4: Surfline API Client

**Files:**
- Create: `surfline_api.py`
- Create: `tests/test_surfline_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_surfline_api.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_surfline_api.py -v`
Expected: FAIL — `No module named 'surfline_api'`

- [ ] **Step 3: Implement Surfline API client**

```python
# surfline_api.py
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_surfline_api.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add surfline_api.py tests/test_surfline_api.py
git commit -m "feat: add Surfline unofficial API client"
```

---

### Task 5: Open-Meteo Fallback API Client

**Files:**
- Create: `openmeteo_api.py`
- Create: `tests/test_openmeteo_api.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_openmeteo_api.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_openmeteo_api.py -v`
Expected: FAIL — `No module named 'openmeteo_api'`

- [ ] **Step 3: Implement Open-Meteo client**

```python
# openmeteo_api.py
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
        # Open-ocean data gives a single height — use a +/- 0.5ft range
        wave_min = round(wave_height_ft - 0.5, 1)
        wave_max = round(wave_height_ft + 0.5, 1)
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_openmeteo_api.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add openmeteo_api.py tests/test_openmeteo_api.py
git commit -m "feat: add Open-Meteo marine wave API fallback client"
```

---

### Task 6: Config Manager

**Files:**
- Create: `config_manager.py`
- Create: `tests/test_config_manager.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_config_manager.py
import json
import os
from config_manager import load_config, save_config, DEFAULT_CONFIG


def test_load_config_creates_default(tmp_path):
    path = tmp_path / "config.json"
    config = load_config(str(path))
    assert config["default_radius_miles"] == 30
    assert config["gmail_address"] == ""


def test_save_and_load_config(tmp_path):
    path = tmp_path / "config.json"
    config = DEFAULT_CONFIG.copy()
    config["home_location"] = "92672"
    config["gmail_address"] = "test@gmail.com"
    save_config(config, str(path))

    loaded = load_config(str(path))
    assert loaded["home_location"] == "92672"
    assert loaded["gmail_address"] == "test@gmail.com"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config_manager.py -v`
Expected: FAIL — `No module named 'config_manager'`

- [ ] **Step 3: Implement config manager**

```python
# config_manager.py
import json
import os

DEFAULT_CONFIG = {
    "gmail_address": "",
    "gmail_app_password": "",
    "home_location": "",
    "default_region": "socal",
    "default_radius_miles": 30,
}


def load_config(path: str = "config.json") -> dict:
    """Load config from file. Returns defaults if file doesn't exist."""
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_config(config: dict, path: str = "config.json"):
    """Save config to file."""
    with open(path, "w") as f:
        json.dump(config, f, indent=2)


def first_run_setup(config_path: str = "config.json") -> dict:
    """Interactive first-run setup. Returns the new config."""
    print("\n  First-time setup:")
    gmail = input("  Gmail address: ").strip()
    app_pw = input("  App password: ").strip()
    home = input("  Home zip/city: ").strip()

    config = DEFAULT_CONFIG.copy()
    config["gmail_address"] = gmail
    config["gmail_app_password"] = app_pw
    config["home_location"] = home
    save_config(config, config_path)
    print("  Saved!\n")
    return config


def settings_menu(config: dict, config_path: str = "config.json") -> dict:
    """Interactive settings menu. Returns updated config."""
    while True:
        print(f"\n  Settings:")
        print(f"    1) Update Gmail credentials")
        print(f"    2) Set home location (current: {config.get('home_location', 'not set')})")
        print(f"    3) Set default region (current: {config.get('default_region', 'socal')})")
        print(f"    4) Set search radius (current: {config.get('default_radius_miles', 30)} miles)")
        print(f"    B) Back")

        choice = input("\n  Choice: ").strip().upper()
        if choice == "1":
            config["gmail_address"] = input("  Gmail address: ").strip()
            config["gmail_app_password"] = input("  App password: ").strip()
            save_config(config, config_path)
            print("  Updated!")
        elif choice == "2":
            config["home_location"] = input("  Home zip/city: ").strip()
            save_config(config, config_path)
            print("  Updated!")
        elif choice == "3":
            config["default_region"] = input("  Default region name: ").strip().lower()
            save_config(config, config_path)
            print("  Updated!")
        elif choice == "4":
            try:
                config["default_radius_miles"] = int(input("  Radius in miles: ").strip())
                save_config(config, config_path)
                print("  Updated!")
            except ValueError:
                print("  Invalid number.")
        elif choice == "B":
            break
    return config
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_config_manager.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add config_manager.py tests/test_config_manager.py
git commit -m "feat: add config manager with load/save and settings menu"
```

---

### Task 7: Contacts Manager

**Files:**
- Create: `contacts_manager.py`
- Create: `tests/test_contacts_manager.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_contacts_manager.py
import json
from contacts_manager import load_contacts, save_contacts, add_contact, delete_contact, CARRIERS


def test_load_contacts_empty(tmp_path):
    path = tmp_path / "contacts.json"
    contacts = load_contacts(str(path))
    assert contacts == []


def test_add_and_load_contact(tmp_path):
    path = tmp_path / "contacts.json"
    contacts = []
    contact = {"name": "Jake", "phone": "9495551234", "carrier": "tmobile", "email": "jake@gmail.com"}
    contacts = add_contact(contacts, contact)
    save_contacts(contacts, str(path))

    loaded = load_contacts(str(path))
    assert len(loaded) == 1
    assert loaded[0]["name"] == "Jake"
    assert loaded[0]["phone"] == "9495551234"


def test_delete_contact():
    contacts = [
        {"name": "Jake", "phone": "9495551234", "carrier": "tmobile", "email": ""},
        {"name": "Sarah", "phone": "", "carrier": "", "email": "sarah@gmail.com"},
    ]
    contacts = delete_contact(contacts, 0)
    assert len(contacts) == 1
    assert contacts[0]["name"] == "Sarah"


def test_carriers_dict():
    assert "tmobile" in CARRIERS
    assert "att" in CARRIERS
    assert "verizon" in CARRIERS
    assert "@" in CARRIERS["tmobile"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_contacts_manager.py -v`
Expected: FAIL — `No module named 'contacts_manager'`

- [ ] **Step 3: Implement contacts manager**

```python
# contacts_manager.py
import json
import os

CARRIERS = {
    "tmobile": "{number}@tmomail.net",
    "att": "{number}@txt.att.net",
    "verizon": "{number}@vtext.com",
    "cricket": "{number}@sms.cricketwireless.net",
    "metro": "{number}@mymetropcs.com",
    "boost": "{number}@sms.myboostmobile.com",
    "uscellular": "{number}@email.uscc.net",
    "mint": "{number}@mailmymobile.net",
}

CARRIER_DISPLAY = {
    "tmobile": "T-Mobile",
    "att": "AT&T",
    "verizon": "Verizon",
    "cricket": "Cricket",
    "metro": "Metro by T-Mobile",
    "boost": "Boost Mobile",
    "uscellular": "US Cellular",
    "mint": "Mint Mobile",
}

CARRIER_KEYS = list(CARRIERS.keys())


def load_contacts(path: str = "contacts.json") -> list:
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []


def save_contacts(contacts: list, path: str = "contacts.json"):
    with open(path, "w") as f:
        json.dump(contacts, f, indent=2)


def add_contact(contacts: list, contact: dict) -> list:
    contacts.append(contact)
    return contacts


def delete_contact(contacts: list, index: int) -> list:
    contacts.pop(index)
    return contacts


def get_sms_address(phone: str, carrier: str) -> str:
    """Convert phone + carrier to SMS email gateway address."""
    template = CARRIERS.get(carrier, "")
    return template.replace("{number}", phone)


def display_contact(contact: dict) -> str:
    """Format a contact for display."""
    parts = [contact["name"]]
    if contact.get("phone"):
        carrier_name = CARRIER_DISPLAY.get(contact.get("carrier", ""), contact.get("carrier", ""))
        parts.append(f"{contact['phone']} ({carrier_name})")
    if contact.get("email"):
        parts.append(contact["email"])
    return " — ".join(parts[1:]) if len(parts) > 1 else parts[0]


def prompt_carrier() -> str:
    """Display carrier menu and return carrier key."""
    print("    Carrier:")
    for i, key in enumerate(CARRIER_KEYS):
        col1 = f"      {i + 1}) {CARRIER_DISPLAY[key]}"
        # Print in two columns
        if i % 2 == 0 and i + 1 < len(CARRIER_KEYS):
            col2 = f"{i + 2}) {CARRIER_DISPLAY[CARRIER_KEYS[i + 1]]}"
            print(f"{col1:<30}{col2}")
        elif i % 2 == 0:
            print(col1)
    while True:
        try:
            choice = int(input("    Carrier #: ").strip()) - 1
            if 0 <= choice < len(CARRIER_KEYS):
                return CARRIER_KEYS[choice]
        except ValueError:
            pass
        print("    Invalid choice. Try again.")


def prompt_new_contact() -> dict:
    """Interactive prompt to create a new contact."""
    name = input("    Name: ").strip()
    phone = input("    Phone # (or skip): ").strip()
    carrier = ""
    if phone and phone.lower() != "skip":
        carrier = prompt_carrier()
    else:
        phone = ""
    email = input("    Email (or skip): ").strip()
    if email.lower() == "skip":
        email = ""

    return {"name": name, "phone": phone, "carrier": carrier, "email": email}


def contacts_menu(contacts: list, contacts_path: str = "contacts.json") -> list:
    """Interactive contacts management menu."""
    while True:
        print("\n  Contacts:")
        if contacts:
            for i, c in enumerate(contacts):
                print(f"    {i + 1}) {c['name']} — {display_contact(c)}")
        else:
            print("    (no contacts saved)")

        print(f"\n    A) Add contact")
        print(f"    E) Edit contact")
        print(f"    D) Delete contact")
        print(f"    B) Back")

        choice = input("\n  Choice: ").strip().upper()
        if choice == "A":
            contact = prompt_new_contact()
            contacts = add_contact(contacts, contact)
            save_contacts(contacts, contacts_path)
            print(f"    Saved \"{contact['name']}\"!")
        elif choice == "E" and contacts:
            try:
                idx = int(input("    Contact # to edit: ").strip()) - 1
                if 0 <= idx < len(contacts):
                    print(f"    Editing {contacts[idx]['name']} (press Enter to keep current):")
                    name = input(f"    Name [{contacts[idx]['name']}]: ").strip()
                    if name:
                        contacts[idx]["name"] = name
                    phone = input(f"    Phone [{contacts[idx].get('phone', '')}]: ").strip()
                    if phone:
                        contacts[idx]["phone"] = phone
                        contacts[idx]["carrier"] = prompt_carrier()
                    email = input(f"    Email [{contacts[idx].get('email', '')}]: ").strip()
                    if email:
                        contacts[idx]["email"] = email
                    save_contacts(contacts, contacts_path)
                    print("    Updated!")
            except (ValueError, IndexError):
                print("    Invalid choice.")
        elif choice == "D" and contacts:
            try:
                idx = int(input("    Contact # to delete: ").strip()) - 1
                if 0 <= idx < len(contacts):
                    name = contacts[idx]["name"]
                    contacts = delete_contact(contacts, idx)
                    save_contacts(contacts, contacts_path)
                    print(f"    Deleted \"{name}\".")
            except (ValueError, IndexError):
                print("    Invalid choice.")
        elif choice == "B":
            break
    return contacts
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_contacts_manager.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add contacts_manager.py tests/test_contacts_manager.py
git commit -m "feat: add contacts manager with CRUD and carrier gateway support"
```

---

### Task 8: Regions Manager

**Files:**
- Create: `regions_manager.py`
- Create: `tests/test_regions_manager.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_regions_manager.py
import json
import os
from regions_manager import load_region, save_region, list_regions, add_spot, remove_spot


def test_load_region_empty(tmp_path):
    spots_dir = tmp_path / "spots"
    spots_dir.mkdir()
    path = spots_dir / "hawaii.json"
    path.write_text("[]")
    spots = load_region(str(path))
    assert spots == []


def test_save_and_load_region(tmp_path):
    spots_dir = tmp_path / "spots"
    spots_dir.mkdir()
    path = spots_dir / "test.json"
    spots = [{"name": "Test Spot", "lat": 33.0, "lon": -117.0, "surfline_id": "", "parking_lat": 33.0, "parking_lon": -117.0, "parking_cost": "Free", "parking_notes": ""}]
    save_region(spots, str(path))
    loaded = load_region(str(path))
    assert len(loaded) == 1
    assert loaded[0]["name"] == "Test Spot"


def test_list_regions(tmp_path):
    spots_dir = tmp_path / "spots"
    spots_dir.mkdir()
    (spots_dir / "socal.json").write_text('[{"name": "A"}, {"name": "B"}]')
    (spots_dir / "hawaii.json").write_text('[{"name": "C"}]')
    regions = list_regions(str(spots_dir))
    assert len(regions) == 2
    names = [r[0] for r in regions]
    assert "socal" in names
    assert "hawaii" in names


def test_add_spot():
    spots = []
    spot = {"name": "New Spot", "lat": 21.0, "lon": -157.0, "surfline_id": "", "parking_lat": 21.0, "parking_lon": -157.0, "parking_cost": "Free", "parking_notes": ""}
    spots = add_spot(spots, spot)
    assert len(spots) == 1
    assert spots[0]["name"] == "New Spot"


def test_remove_spot():
    spots = [
        {"name": "A", "lat": 1.0, "lon": 1.0},
        {"name": "B", "lat": 2.0, "lon": 2.0},
    ]
    spots = remove_spot(spots, 0)
    assert len(spots) == 1
    assert spots[0]["name"] == "B"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_regions_manager.py -v`
Expected: FAIL — `No module named 'regions_manager'`

- [ ] **Step 3: Implement regions manager**

```python
# regions_manager.py
import json
import os


def load_region(path: str) -> list:
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []


def save_region(spots: list, path: str):
    with open(path, "w") as f:
        json.dump(spots, f, indent=2)


def list_regions(spots_dir: str = "spots") -> list:
    """Return list of (name, count, path) for each region file."""
    regions = []
    if not os.path.exists(spots_dir):
        return regions
    for filename in sorted(os.listdir(spots_dir)):
        if filename.endswith(".json"):
            path = os.path.join(spots_dir, filename)
            name = filename.replace(".json", "")
            spots = load_region(path)
            regions.append((name, len(spots), path))
    return regions


def add_spot(spots: list, spot: dict) -> list:
    spots.append(spot)
    return spots


def remove_spot(spots: list, index: int) -> list:
    spots.pop(index)
    return spots


def prompt_new_spot() -> dict:
    """Interactive prompt to add a new spot."""
    name = input("    Spot name: ").strip()
    try:
        lat = float(input("    Latitude: ").strip())
        lon = float(input("    Longitude: ").strip())
    except ValueError:
        print("    Invalid coordinates.")
        return None

    surfline_id = input("    Surfline ID (or skip): ").strip()
    if surfline_id.lower() == "skip":
        surfline_id = ""

    parking_input = input("    Parking lat (or 'same'): ").strip()
    if parking_input.lower() == "same" or not parking_input:
        parking_lat, parking_lon = lat, lon
    else:
        try:
            parking_lat = float(parking_input)
            parking_lon = float(input("    Parking lon: ").strip())
        except ValueError:
            parking_lat, parking_lon = lat, lon

    parking_cost = input("    Parking cost (e.g., Free, $15/day): ").strip() or "Unknown"
    parking_notes = input("    Parking notes (or skip): ").strip()
    if parking_notes.lower() == "skip":
        parking_notes = ""

    return {
        "name": name,
        "lat": lat,
        "lon": lon,
        "surfline_id": surfline_id,
        "parking_lat": parking_lat,
        "parking_lon": parking_lon,
        "parking_cost": parking_cost,
        "parking_notes": parking_notes,
    }


def regions_menu(spots_dir: str = "spots"):
    """Interactive regions management menu."""
    os.makedirs(spots_dir, exist_ok=True)

    while True:
        regions = list_regions(spots_dir)
        print("\n  Spot Regions:")
        if regions:
            for i, (name, count, path) in enumerate(regions):
                print(f"    {i + 1}) {name.title()} ({count} spots)")
        else:
            print("    (no regions)")

        print(f"\n    A) Add new region")
        print(f"    D) Delete a region")
        print(f"    S) Add/remove spots in a region")
        print(f"    B) Back")

        choice = input("\n  Choice: ").strip().upper()
        if choice == "A":
            name = input("    Region name: ").strip().lower().replace(" ", "_")
            path = os.path.join(spots_dir, f"{name}.json")
            save_region([], path)
            print(f"    Created \"{name}\" (0 spots)")
            if input("    Add a spot now? (y/n): ").strip().lower() == "y":
                spots = []
                while True:
                    spot = prompt_new_spot()
                    if spot:
                        spots = add_spot(spots, spot)
                        save_region(spots, path)
                        print(f"    Added \"{spot['name']}\"!")
                    if input("    Add another? (y/n): ").strip().lower() != "y":
                        break
        elif choice == "D" and regions:
            try:
                idx = int(input("    Region # to delete: ").strip()) - 1
                if 0 <= idx < len(regions):
                    name, _, path = regions[idx]
                    confirm = input(f"    Delete \"{name}\"? (y/n): ").strip().lower()
                    if confirm == "y":
                        os.remove(path)
                        print(f"    Deleted \"{name}\".")
            except (ValueError, IndexError):
                print("    Invalid choice.")
        elif choice == "S" and regions:
            try:
                idx = int(input("    Region #: ").strip()) - 1
                if 0 <= idx < len(regions):
                    name, _, path = regions[idx]
                    spots = load_region(path)
                    print(f"\n    Spots in {name.title()}:")
                    for i, s in enumerate(spots):
                        print(f"      {i + 1}) {s['name']}")
                    action = input("\n    A) Add spot  R) Remove spot  B) Back: ").strip().upper()
                    if action == "A":
                        spot = prompt_new_spot()
                        if spot:
                            spots = add_spot(spots, spot)
                            save_region(spots, path)
                            print(f"    Added \"{spot['name']}\"!")
                    elif action == "R" and spots:
                        si = int(input("    Spot # to remove: ").strip()) - 1
                        if 0 <= si < len(spots):
                            removed = spots[si]["name"]
                            spots = remove_spot(spots, si)
                            save_region(spots, path)
                            print(f"    Removed \"{removed}\".")
            except (ValueError, IndexError):
                print("    Invalid choice.")
        elif choice == "B":
            break
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_regions_manager.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add regions_manager.py tests/test_regions_manager.py
git commit -m "feat: add regions manager with multi-region spot CRUD"
```

---

### Task 9: Messaging (Email + SMS)

**Files:**
- Create: `messaging.py`
- Create: `tests/test_messaging.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_messaging.py
from unittest.mock import patch, MagicMock
from messaging import send_email, send_sms, build_spot_message


def test_build_spot_message():
    spot = {"name": "T-Street", "parking_cost": "Free", "parking_notes": ""}
    conditions = {
        "wave_min": 2, "wave_max": 3,
        "condition_rating": "Fair",
        "tide_trend": "Rising",
        "wind_direction_type": "Offshore",
    }
    directions_url = "https://www.google.com/maps/dir/?api=1&destination=33.4,-117.6"
    subject, body = build_spot_message(spot, conditions, directions_url)
    assert "T-Street" in subject
    assert "2-3" in subject
    assert "Rising" in body
    assert "Offshore" in body
    assert "Free" in body
    assert directions_url in body


def test_send_email_calls_smtp():
    with patch("messaging.smtplib.SMTP_SSL") as mock_smtp_class:
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        result = send_email(
            gmail_address="test@gmail.com",
            gmail_password="password",
            to_address="friend@gmail.com",
            subject="Surf Alert",
            body="Test body",
        )
        assert result is True


def test_send_sms_calls_smtp():
    with patch("messaging.smtplib.SMTP_SSL") as mock_smtp_class:
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_smtp)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        result = send_sms(
            gmail_address="test@gmail.com",
            gmail_password="password",
            sms_gateway_address="9495551234@tmomail.net",
            body="Test SMS",
        )
        assert result is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_messaging.py -v`
Expected: FAIL — `No module named 'messaging'`

- [ ] **Step 3: Implement messaging**

```python
# messaging.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def build_spot_message(spot: dict, conditions: dict, directions_url: str) -> tuple:
    """Build subject and body for a spot notification. Returns (subject, body)."""
    name = spot["name"]
    wave_min = conditions["wave_min"]
    wave_max = conditions["wave_max"]
    rating = conditions["condition_rating"]
    tide = conditions["tide_trend"]
    wind = conditions["wind_direction_type"]
    parking = spot.get("parking_cost", "Unknown")
    parking_notes = spot.get("parking_notes", "")

    subject = f"Surf Alert: {name} — {wave_min}-{wave_max}ft"

    body_lines = [
        f"{name} — {wave_min}-{wave_max}ft, {rating}",
        f"Tide: {tide} | Wind: {wind}",
        f"Parking: {parking}",
    ]
    if parking_notes:
        body_lines.append(f"  ({parking_notes})")
    body_lines.append(directions_url)

    return subject, "\n".join(body_lines)


def send_email(gmail_address: str, gmail_password: str, to_address: str, subject: str, body: str) -> bool:
    """Send an email via Gmail SMTP. Returns True on success, False on failure."""
    try:
        msg = MIMEMultipart()
        msg["From"] = gmail_address
        msg["To"] = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"    Email send failed: {e}")
        return False


def send_sms(gmail_address: str, gmail_password: str, sms_gateway_address: str, body: str) -> bool:
    """Send SMS via carrier email gateway. Returns True on success, False on failure."""
    try:
        msg = MIMEText(body)
        msg["From"] = gmail_address
        msg["To"] = sms_gateway_address

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"    SMS send failed: {e}")
        return False
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_messaging.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add messaging.py tests/test_messaging.py
git commit -m "feat: add email and SMS messaging via Gmail SMTP"
```

---

### Task 10: SoCal Spots Data File

**Files:**
- Create: `spots/socal.json`

- [ ] **Step 1: Create the spots directory**

```bash
mkdir -p spots
```

- [ ] **Step 2: Create socal.json with pre-populated spots**

Create `spots/socal.json` with ~50 SoCal surf spots. Each entry must have: `name`, `lat`, `lon`, `surfline_id`, `parking_lat`, `parking_lon`, `parking_cost`, `parking_notes`.

The full data file should include spots from Ventura County to the Mexican border. Surfline spot IDs can be found by visiting each spot's Surfline page and extracting the ID from the URL (format: `surfline.com/surf-report/{slug}/{spot_id}`).

Here are the first several entries as a template — the full file should contain approximately 50 spots:

```json
[
  {
    "name": "Rincon",
    "lat": 34.3742,
    "lon": -119.4780,
    "surfline_id": "5842041f4e65fad6a7708cfc",
    "parking_lat": 34.3738,
    "parking_lon": -119.4776,
    "parking_cost": "Free",
    "parking_notes": "Limited lot, fills early on good days"
  },
  {
    "name": "Ventura Point (C Street)",
    "lat": 34.2743,
    "lon": -119.3070,
    "surfline_id": "5842041f4e65fad6a7708cfb",
    "parking_lat": 34.2740,
    "parking_lon": -119.3065,
    "parking_cost": "Free",
    "parking_notes": "Street parking along Shoreline Dr"
  },
  {
    "name": "Mondos",
    "lat": 34.3520,
    "lon": -119.4400,
    "surfline_id": "5842041f4e65fad6a7708cf7",
    "parking_lat": 34.3515,
    "parking_lon": -119.4395,
    "parking_cost": "Free",
    "parking_notes": "Dirt lot off PCH"
  },
  {
    "name": "County Line",
    "lat": 34.0510,
    "lon": -118.9640,
    "surfline_id": "5842041f4e65fad6a7708cf2",
    "parking_lat": 34.0507,
    "parking_lon": -118.9635,
    "parking_cost": "Free",
    "parking_notes": "PCH shoulder parking"
  },
  {
    "name": "Zuma Beach",
    "lat": 34.0152,
    "lon": -118.8225,
    "surfline_id": "5842041f4e65fad6a7708cef",
    "parking_lat": 34.0148,
    "parking_lon": -118.8220,
    "parking_cost": "$8-$15/day",
    "parking_notes": "LA County lot, pay at entrance"
  },
  {
    "name": "Malibu (Surfrider)",
    "lat": 34.0362,
    "lon": -118.6797,
    "surfline_id": "5842041f4e65fad6a7708ced",
    "parking_lat": 34.0358,
    "parking_lon": -118.6800,
    "parking_cost": "$8-$15/day",
    "parking_notes": "Adamson House lot or PCH metered"
  },
  {
    "name": "Topanga",
    "lat": 34.0380,
    "lon": -118.5870,
    "surfline_id": "5842041f4e65fad6a7708ce9",
    "parking_lat": 34.0375,
    "parking_lon": -118.5865,
    "parking_cost": "$8-$15/day",
    "parking_notes": "State beach lot"
  },
  {
    "name": "El Porto",
    "lat": 33.8965,
    "lon": -118.4210,
    "surfline_id": "5842041f4e65fad6a7708ce4",
    "parking_lat": 33.8960,
    "parking_lon": -118.4205,
    "parking_cost": "Free-$2/hr",
    "parking_notes": "Street parking or metered lot"
  },
  {
    "name": "Manhattan Beach",
    "lat": 33.8847,
    "lon": -118.4120,
    "surfline_id": "5842041f4e65fad6a7708ce3",
    "parking_lat": 33.8843,
    "parking_lon": -118.4115,
    "parking_cost": "$2/hr metered",
    "parking_notes": "Metered street parking"
  },
  {
    "name": "Hermosa Beach",
    "lat": 33.8622,
    "lon": -118.4010,
    "surfline_id": "5842041f4e65fad6a7708ce1",
    "parking_lat": 33.8618,
    "parking_lon": -118.4005,
    "parking_cost": "$2/hr metered",
    "parking_notes": "Metered lots near pier"
  },
  {
    "name": "Torrance Beach (RAT Beach)",
    "lat": 33.8050,
    "lon": -118.3940,
    "surfline_id": "5842041f4e65fad6a7708cde",
    "parking_lat": 33.8045,
    "parking_lon": -118.3935,
    "parking_cost": "Free",
    "parking_notes": "Lot at end of Paseo de la Playa"
  },
  {
    "name": "Huntington Beach Pier",
    "lat": 33.6553,
    "lon": -117.9992,
    "surfline_id": "5842041f4e65fad6a7708968",
    "parking_lat": 33.6548,
    "parking_lon": -117.9988,
    "parking_cost": "$2/hr metered",
    "parking_notes": "Metered lot near pier, free street parking blocks back"
  },
  {
    "name": "Huntington Beach Cliffs",
    "lat": 33.6370,
    "lon": -117.9780,
    "surfline_id": "5842041f4e65fad6a7708967",
    "parking_lat": 33.6365,
    "parking_lon": -117.9775,
    "parking_cost": "Free",
    "parking_notes": "Free parking along PCH bluffs"
  },
  {
    "name": "56th Street (Newport)",
    "lat": 33.6140,
    "lon": -117.9370,
    "surfline_id": "5842041f4e65fad6a7708963",
    "parking_lat": 33.6135,
    "parking_lon": -117.9365,
    "parking_cost": "Free-$2/hr",
    "parking_notes": "Street parking, some metered"
  },
  {
    "name": "Newport Beach Pier",
    "lat": 33.6070,
    "lon": -117.9300,
    "surfline_id": "5842041f4e65fad6a7708962",
    "parking_lat": 33.6065,
    "parking_lon": -117.9295,
    "parking_cost": "$2/hr metered",
    "parking_notes": "Metered parking near pier"
  },
  {
    "name": "Blackies (Newport)",
    "lat": 33.5970,
    "lon": -117.9260,
    "surfline_id": "5842041f4e65fad6a7708960",
    "parking_lat": 33.5965,
    "parking_lon": -117.9255,
    "parking_cost": "Free",
    "parking_notes": "Street parking near jetty"
  },
  {
    "name": "The Wedge",
    "lat": 33.5930,
    "lon": -117.8820,
    "surfline_id": "5842041f4e65fad6a770895e",
    "parking_lat": 33.5925,
    "parking_lon": -117.8815,
    "parking_cost": "Free",
    "parking_notes": "Street parking on Balboa Peninsula"
  },
  {
    "name": "Salt Creek",
    "lat": 33.4710,
    "lon": -117.7230,
    "surfline_id": "5842041f4e65fad6a770889c",
    "parking_lat": 33.4705,
    "parking_lon": -117.7225,
    "parking_cost": "$1/hr",
    "parking_notes": "Metered lot at Salt Creek Beach Park"
  },
  {
    "name": "Dana Point (Doheny)",
    "lat": 33.4600,
    "lon": -117.6870,
    "surfline_id": "5842041f4e65fad6a7708899",
    "parking_lat": 33.4595,
    "parking_lon": -117.6865,
    "parking_cost": "$15/day",
    "parking_notes": "State beach day-use fee"
  },
  {
    "name": "T-Street (San Clemente)",
    "lat": 33.4175,
    "lon": -117.6230,
    "surfline_id": "5842041f4e65fad6a7708895",
    "parking_lat": 33.4170,
    "parking_lon": -117.6225,
    "parking_cost": "Free",
    "parking_notes": "Residential street parking on T-Street"
  },
  {
    "name": "San Clemente Pier",
    "lat": 33.4190,
    "lon": -117.6240,
    "surfline_id": "5842041f4e65fad6a7708894",
    "parking_lat": 33.4185,
    "parking_lon": -117.6235,
    "parking_cost": "Free-$2/hr",
    "parking_notes": "Metered near pier, free on side streets"
  },
  {
    "name": "Cottons (Trestles)",
    "lat": 33.3880,
    "lon": -117.5920,
    "surfline_id": "5842041f4e65fad6a7708893",
    "parking_lat": 33.3830,
    "parking_lon": -117.5880,
    "parking_cost": "Free",
    "parking_notes": "Park at Carl's Jr lot or Cristianitos. Walk or bike in."
  },
  {
    "name": "Uppers (Trestles)",
    "lat": 33.3860,
    "lon": -117.5910,
    "surfline_id": "5842041f4e65fad6a7708892",
    "parking_lat": 33.3830,
    "parking_lon": -117.5880,
    "parking_cost": "Free",
    "parking_notes": "Same walk-in as Lowers/Cottons"
  },
  {
    "name": "Lowers (Trestles)",
    "lat": 33.3822,
    "lon": -117.5893,
    "surfline_id": "5842041f4e65fad6a7708890",
    "parking_lat": 33.3830,
    "parking_lon": -117.5880,
    "parking_cost": "Free",
    "parking_notes": "Walk-in or bike only. Carl's Jr lot or Cristianitos Rd."
  },
  {
    "name": "Middles (Trestles)",
    "lat": 33.3840,
    "lon": -117.5900,
    "surfline_id": "5842041f4e65fad6a7708891",
    "parking_lat": 33.3830,
    "parking_lon": -117.5880,
    "parking_cost": "Free",
    "parking_notes": "Same walk-in as Lowers"
  },
  {
    "name": "San Onofre (Old Man's)",
    "lat": 33.3720,
    "lon": -117.5690,
    "surfline_id": "5842041f4e65fad6a770888e",
    "parking_lat": 33.3715,
    "parking_lon": -117.5685,
    "parking_cost": "$15/day",
    "parking_notes": "San Onofre State Beach day-use fee"
  },
  {
    "name": "Oceanside Pier",
    "lat": 33.1930,
    "lon": -117.3890,
    "surfline_id": "5842041f4e65fad6a770888b",
    "parking_lat": 33.1925,
    "parking_lon": -117.3885,
    "parking_cost": "Free-$2/hr",
    "parking_notes": "Free on The Strand, metered near pier"
  },
  {
    "name": "Oceanside Harbor",
    "lat": 33.2070,
    "lon": -117.3960,
    "surfline_id": "5842041f4e65fad6a770888c",
    "parking_lat": 33.2065,
    "parking_lon": -117.3955,
    "parking_cost": "Free",
    "parking_notes": "Harbor parking lot"
  },
  {
    "name": "Cardiff Reef",
    "lat": 33.0210,
    "lon": -117.2890,
    "surfline_id": "5842041f4e65fad6a7708887",
    "parking_lat": 33.0205,
    "parking_lon": -117.2885,
    "parking_cost": "Free",
    "parking_notes": "Lot at Cardiff State Beach or Restaurant Row"
  },
  {
    "name": "Swamis",
    "lat": 33.0340,
    "lon": -117.2930,
    "surfline_id": "5842041f4e65fad6a7708886",
    "parking_lat": 33.0335,
    "parking_lon": -117.2925,
    "parking_cost": "Free",
    "parking_notes": "Small lot at Swami's park, street parking on 1st St"
  },
  {
    "name": "Pipes (Cardiff)",
    "lat": 33.0130,
    "lon": -117.2830,
    "surfline_id": "5842041f4e65fad6a7708888",
    "parking_lat": 33.0125,
    "parking_lon": -117.2825,
    "parking_cost": "Free",
    "parking_notes": "Parking along coast highway"
  },
  {
    "name": "Del Mar (15th Street)",
    "lat": 32.9620,
    "lon": -117.2700,
    "surfline_id": "5842041f4e65fad6a7708884",
    "parking_lat": 32.9615,
    "parking_lon": -117.2695,
    "parking_cost": "Free-$3/hr",
    "parking_notes": "Metered near beach, free on side streets"
  },
  {
    "name": "Black's Beach",
    "lat": 32.8890,
    "lon": -117.2530,
    "surfline_id": "5842041f4e65fad6a7708882",
    "parking_lat": 32.8870,
    "parking_lon": -117.2510,
    "parking_cost": "Free",
    "parking_notes": "Gliderport lot at top of cliffs. Steep trail down."
  },
  {
    "name": "La Jolla Shores",
    "lat": 32.8560,
    "lon": -117.2570,
    "surfline_id": "5842041f4e65fad6a7708880",
    "parking_lat": 32.8555,
    "parking_lon": -117.2565,
    "parking_cost": "Free",
    "parking_notes": "Free lot at Kellogg Park, fills fast"
  },
  {
    "name": "Windansea",
    "lat": 32.8300,
    "lon": -117.2800,
    "surfline_id": "5842041f4e65fad6a770887e",
    "parking_lat": 32.8295,
    "parking_lon": -117.2795,
    "parking_cost": "Free",
    "parking_notes": "Residential street parking on Neptune Pl"
  },
  {
    "name": "Pacific Beach (Tourmaline)",
    "lat": 32.8050,
    "lon": -117.2640,
    "surfline_id": "5842041f4e65fad6a770887c",
    "parking_lat": 32.8045,
    "parking_lon": -117.2635,
    "parking_cost": "Free",
    "parking_notes": "Tourmaline Surfing Park lot, fills by 8am weekends"
  },
  {
    "name": "Pacific Beach Pier",
    "lat": 32.7950,
    "lon": -117.2560,
    "surfline_id": "5842041f4e65fad6a770887b",
    "parking_lat": 32.7945,
    "parking_lon": -117.2555,
    "parking_cost": "Free-$2/hr",
    "parking_notes": "Metered near pier, free blocks back"
  },
  {
    "name": "Mission Beach",
    "lat": 32.7740,
    "lon": -117.2530,
    "surfline_id": "5842041f4e65fad6a770887a",
    "parking_lat": 32.7735,
    "parking_lon": -117.2525,
    "parking_cost": "Free-$2/hr",
    "parking_notes": "Belmont Park area, metered and free"
  },
  {
    "name": "Ocean Beach Pier",
    "lat": 32.7480,
    "lon": -117.2540,
    "surfline_id": "5842041f4e65fad6a7708878",
    "parking_lat": 32.7475,
    "parking_lon": -117.2535,
    "parking_cost": "Free",
    "parking_notes": "Free lot at pier, street parking on Newport Ave"
  },
  {
    "name": "Sunset Cliffs",
    "lat": 32.7200,
    "lon": -117.2560,
    "surfline_id": "5842041f4e65fad6a7708876",
    "parking_lat": 32.7195,
    "parking_lon": -117.2555,
    "parking_cost": "Free",
    "parking_notes": "Street parking along Sunset Cliffs Blvd"
  },
  {
    "name": "Imperial Beach Pier",
    "lat": 32.5790,
    "lon": -117.1340,
    "surfline_id": "5842041f4e65fad6a7708874",
    "parking_lat": 32.5785,
    "parking_lon": -117.1335,
    "parking_cost": "Free",
    "parking_notes": "Free lot near pier"
  }
]
```

Note: Surfline spot IDs listed above are representative. During implementation, verify each ID by checking `https://services.surfline.com/kbyg/spots/forecasts/conditions?spotId={id}&days=1` returns valid data. Update any IDs that return errors.

- [ ] **Step 3: Commit**

```bash
git add spots/socal.json
git commit -m "feat: add pre-populated SoCal surf spots database (41 spots)"
```

---

### Task 11: Main Entry Point — Find Waves Flow + Main Menu

**Files:**
- Create: `surf_finder.py`

- [ ] **Step 1: Implement the find_waves function**

This is the core feature — the "Find waves now" flow. It ties together all the modules.

```python
# surf_finder.py
import os
import sys

from geo import haversine_miles, geocode
from surfline_api import get_surfline_conditions
from openmeteo_api import get_openmeteo_conditions
from config_manager import load_config, save_config, first_run_setup, settings_menu
from contacts_manager import (
    load_contacts, save_contacts, contacts_menu, display_contact,
    get_sms_address, prompt_new_contact, add_contact, CARRIER_KEYS,
)
from regions_manager import list_regions, load_region, regions_menu
from messaging import build_spot_message, send_email, send_sms

APP_DIR = os.path.dirname(os.path.abspath(__file__))
SPOTS_DIR = os.path.join(APP_DIR, "spots")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
CONTACTS_PATH = os.path.join(APP_DIR, "contacts.json")


def directions_url(spot: dict) -> str:
    lat = spot.get("parking_lat", spot["lat"])
    lon = spot.get("parking_lon", spot["lon"])
    return f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}"


def parse_wave_range(text: str) -> tuple | None:
    """Parse '2-3' into (2.0, 3.0). Returns None on invalid input."""
    text = text.strip().replace(" ", "")
    parts = text.split("-")
    if len(parts) != 2:
        return None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None


def ranges_overlap(min1, max1, min2, max2) -> bool:
    return min1 <= max2 and min2 <= max1


def find_waves(config: dict, contacts: list) -> list:
    """Main 'Find waves now' flow. Returns updated contacts list."""
    # Step 1: Select region
    regions = list_regions(SPOTS_DIR)
    if not regions:
        print("\n  No spot regions found. Add one in 'Manage spot regions' first.")
        return contacts

    if len(regions) == 1:
        region_name, region_count, region_path = regions[0]
        print(f"\n  Using region: {region_name.title()} ({region_count} spots)")
    else:
        print("\n  Select region:")
        for i, (name, count, _) in enumerate(regions):
            print(f"    {i + 1}) {name.title()} ({count} spots)")
        try:
            idx = int(input("\n  Region #: ").strip()) - 1
            region_name, region_count, region_path = regions[idx]
        except (ValueError, IndexError):
            print("  Invalid choice.")
            return contacts

    spots = load_region(region_path)
    if not spots:
        print(f"  No spots in {region_name}. Add some first.")
        return contacts

    # Step 2: Enter location
    home = config.get("home_location", "")
    if home:
        loc_input = input(f"\n  Location [{home}]: ").strip()
        if not loc_input:
            loc_input = home
    else:
        loc_input = input("\n  Enter your location (zip or city): ").strip()

    print("  Geocoding...")
    geo_result = geocode(loc_input)
    if not geo_result:
        print("  Could not find that location. Try a zip code or different city name.")
        return contacts

    user_lat, user_lon, location_name = geo_result
    print(f"  Found: {location_name}")

    # Step 3: Enter desired wave size
    wave_input = input("  Desired wave size (e.g., 2-3): ").strip()
    wave_range = parse_wave_range(wave_input)
    if not wave_range:
        print("  Invalid format. Use min-max like '2-3' or '3-4'.")
        return contacts

    desired_min, desired_max = wave_range
    radius = config.get("default_radius_miles", 30)

    # Step 4: Filter by distance
    nearby = []
    for spot in spots:
        dist = haversine_miles(user_lat, user_lon, spot["lat"], spot["lon"])
        if dist <= radius:
            nearby.append((spot, dist))

    if not nearby:
        print(f"\n  No spots found within {radius} miles of {location_name}.")
        return contacts

    print(f"\n  Checking conditions at {len(nearby)} spots within {radius}mi...")

    # Step 5: Query conditions and filter by wave size
    results = []
    for spot, dist in nearby:
        if spot.get("surfline_id"):
            conditions = get_surfline_conditions(spot["surfline_id"])
        else:
            conditions = get_openmeteo_conditions(spot["lat"], spot["lon"])

        if conditions and ranges_overlap(desired_min, desired_max, conditions["wave_min"], conditions["wave_max"]):
            results.append((spot, conditions, dist))

    if not results:
        print(f"\n  No spots with {wave_input}ft waves found near {location_name}.")
        print(f"  ({len(nearby)} spots checked)")
        return contacts

    # Sort by distance (default)
    results.sort(key=lambda x: x[2])

    # Step 6: Display results
    print(f"\n  Surf spots with {wave_input}ft waves within {radius}mi of {location_name}:\n")
    header = f"  {'#':<4}{'Spot':<26}{'Waves':<10}{'Conditions':<14}{'Tide':<10}{'Wind':<12}{'Parking':<18}{'Distance':<10}Directions"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for i, (spot, cond, dist) in enumerate(results):
        waves = f"{cond['wave_min']}-{cond['wave_max']} ft"
        url = directions_url(spot)
        parking = spot.get("parking_cost", "Unknown")
        print(f"  {i+1:<4}{spot['name']:<26}{waves:<10}{cond['condition_rating']:<14}{cond['tide_trend']:<10}{cond['wind_direction_type']:<12}{parking:<18}{dist:<10.1f}{url}")

    print(f"\n  Found {len(results)} spots matching your criteria.")

    # Sort option
    sort_choice = input("\n  Sort by: 1) Distance (current)  2) Best conditions first  (Enter to skip): ").strip()
    if sort_choice == "2":
        results.sort(key=lambda x: x[1]["condition_rank"], reverse=True)
        print()
        print(header)
        print("  " + "-" * (len(header) - 2))
        for i, (spot, cond, dist) in enumerate(results):
            waves = f"{cond['wave_min']}-{cond['wave_max']} ft"
            url = directions_url(spot)
            parking = spot.get("parking_cost", "Unknown")
            print(f"  {i+1:<4}{spot['name']:<26}{waves:<10}{cond['condition_rating']:<14}{cond['tide_trend']:<10}{cond['wind_direction_type']:<12}{parking:<18}{dist:<10.1f}{url}")

    # Step 7: Send directions
    send_choice = input("\n  Send directions? Enter spot # (or 'skip'): ").strip()
    if send_choice.lower() == "skip" or not send_choice:
        return contacts

    try:
        spot_idx = int(send_choice) - 1
        spot, cond, dist = results[spot_idx]
    except (ValueError, IndexError):
        print("  Invalid spot number.")
        return contacts

    # Pick recipient
    print("\n  Send to:")
    for i, c in enumerate(contacts):
        print(f"    {i + 1}) {c['name']} — {display_contact(c)}")
    print(f"    {len(contacts) + 1}) Enter new recipient")

    try:
        recip_choice = int(input("\n  Choice: ").strip()) - 1
    except ValueError:
        print("  Invalid choice.")
        return contacts

    is_new = recip_choice == len(contacts)
    if is_new:
        contact = prompt_new_contact()
    elif 0 <= recip_choice < len(contacts):
        contact = contacts[recip_choice]
    else:
        print("  Invalid choice.")
        return contacts

    # How to send
    can_sms = bool(contact.get("phone") and contact.get("carrier"))
    can_email = bool(contact.get("email"))

    if can_sms and can_email:
        print("\n  How to send?")
        print("    1) Text (SMS)")
        print("    2) Email")
        print("    3) Both")
        method = input("  Choice: ").strip()
    elif can_sms:
        method = "1"
    elif can_email:
        method = "2"
    else:
        print("  Contact has no phone or email.")
        return contacts

    url = directions_url(spot)
    subject, body = build_spot_message(spot, cond, url)
    gmail = config.get("gmail_address", "")
    gmail_pw = config.get("gmail_app_password", "")

    if not gmail or not gmail_pw:
        print("  Gmail not configured. Go to Settings first.")
        return contacts

    sent = False
    if method in ("1", "3") and can_sms:
        sms_addr = get_sms_address(contact["phone"], contact["carrier"])
        if send_sms(gmail, gmail_pw, sms_addr, body):
            sent = True

    if method in ("2", "3") and can_email:
        if send_email(gmail, gmail_pw, contact["email"], subject, body):
            sent = True

    if sent:
        method_name = {
            "1": "text", "2": "email", "3": "text & email"
        }.get(method, "message")
        print(f"\n  Directions to {spot['name']} sent to {contact['name']} via {method_name}!")

    # Offer to save new contact
    if is_new and sent:
        if input("\n  Save this contact for next time? (y/n): ").strip().lower() == "y":
            name = input("    Name: ").strip()
            if name:
                contact["name"] = name
            contacts = add_contact(contacts, contact)
            save_contacts(contacts, CONTACTS_PATH)
            print(f"    Saved \"{contact['name']}\"!")

    return contacts


def main():
    print("\n  LetsGoSurf - Surf Finder\n")

    config = load_config(CONFIG_PATH)
    if not config.get("gmail_address"):
        print("  Welcome! Let's get you set up.\n")
        config = first_run_setup(CONFIG_PATH)

    contacts = load_contacts(CONTACTS_PATH)

    while True:
        print("\n  Main Menu:")
        print("    1) Find waves now")
        print("    2) Manage spot regions")
        print("    3) Manage contacts")
        print("    4) Settings")
        print("    5) Quit")

        choice = input("\n  Choice: ").strip()
        if choice == "1":
            contacts = find_waves(config, contacts)
        elif choice == "2":
            regions_menu(SPOTS_DIR)
        elif choice == "3":
            contacts = contacts_menu(contacts, CONTACTS_PATH)
        elif choice == "4":
            config = settings_menu(config, CONFIG_PATH)
        elif choice == "5":
            print("\n  Hang loose! 🤙\n")
            break
        else:
            print("  Invalid choice. Enter 1-5.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the app manually to smoke test**

Run: `cd C:\Repos\LetsGoSurf && python surf_finder.py`

Verify:
- Main menu displays
- First-run setup prompts if no config exists (you can ctrl+C to skip)
- Menu options 2-5 all respond correctly

- [ ] **Step 3: Commit**

```bash
git add surf_finder.py
git commit -m "feat: add main entry point with find waves flow and main menu"
```

---

### Task 12: Run All Tests + Final Verification

**Files:** No new files.

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass (16 total across all test files)

- [ ] **Step 2: Fix any test failures**

If any tests fail, fix the issues in the relevant files.

- [ ] **Step 3: Run the full app end-to-end**

Run: `python surf_finder.py`

Manual test checklist:
1. First-run setup works (or skip if already configured)
2. "Find waves now" — enter a zip code (e.g., 92672), wave size (e.g., 2-3), see results
3. Google Maps links are clickable in terminal
4. "Manage spot regions" — can list regions, see spot count
5. "Manage contacts" — can add a contact, see it listed
6. "Settings" — can view and change settings
7. "Quit" — exits cleanly

- [ ] **Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: address test and integration issues from final verification"
```

- [ ] **Step 5: Push to GitHub**

```bash
git push origin main
```

---

### Task 13: Verify Surfline Spot IDs

**Files:**
- Modify: `spots/socal.json`

- [ ] **Step 1: Write a quick verification script**

Create a temporary script to test each spot ID:

```python
# verify_spots.py (temporary — delete after use)
import json
import requests
import time

with open("spots/socal.json") as f:
    spots = json.load(f)

for spot in spots:
    sid = spot.get("surfline_id", "")
    if not sid:
        print(f"  SKIP (no ID): {spot['name']}")
        continue
    try:
        resp = requests.get(
            f"https://services.surfline.com/kbyg/spots/forecasts/conditions",
            params={"spotId": sid, "days": 1},
            timeout=10,
        )
        if resp.status_code == 200 and "data" in resp.json():
            print(f"  OK: {spot['name']}")
        else:
            print(f"  FAIL ({resp.status_code}): {spot['name']} — {sid}")
    except Exception as e:
        print(f"  ERROR: {spot['name']} — {e}")
    time.sleep(0.5)  # be polite to Surfline's servers
```

- [ ] **Step 2: Run verification**

Run: `python verify_spots.py`

For any spot that returns FAIL, look up the correct Surfline spot ID by searching `https://www.surfline.com/surf-report/{spot-name-slug}` and extracting the ID from the URL.

- [ ] **Step 3: Update any incorrect IDs in socal.json**

Edit `spots/socal.json` with corrected IDs.

- [ ] **Step 4: Delete verify_spots.py and commit**

```bash
rm verify_spots.py
git add spots/socal.json
git commit -m "fix: verify and correct Surfline spot IDs for SoCal database"
git push origin main
```
