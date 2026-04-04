# Surf Finder — Design Spec

**Date:** 2026-04-04
**Purpose:** A Python CLI app that finds surf spots near you matching your desired wave size, shows current conditions with tide/wind data, provides Google Maps directions, and can text/email results to saved contacts.

---

## Architecture

Single Python CLI application with supporting data files:

```
surf-finder/
  surf_finder.py        # Main script (entry point)
  spots/
    socal.json          # Pre-populated ~50-60 SoCal spots
  contacts.json         # Saved recipients (created on first save)
  config.json           # Gmail creds + user defaults (created on first run)
```

**Dependencies:** `requests` (pip install). Everything else uses Python standard library (`smtplib`, `json`, `math`, `email`).

---

## Main Menu

```
Surf Finder

  1) Find waves now
  2) Manage spot regions
  3) Manage contacts
  4) Settings
  5) Quit
```

---

## Feature 1: Find Waves Now

### Flow

1. **Select region** — if multiple regions exist, numbered menu. If only one, auto-selects it.
2. **Enter location** — shows saved home location from config with option to override. Accepts zip code or city name.
3. **Enter desired wave size** — format is `min-max` in feet, e.g., `2-3` or `3-4`. The app matches spots where the current wave range overlaps the requested range (e.g., a spot reporting 2-4ft matches a request for 3-4ft).
4. **Geocode location** — convert zip/city to lat/lon.
5. **Filter spots by distance** — haversine formula, keep spots within configured radius (default 30 miles).
6. **Query conditions** — hit Surfline API (or Open-Meteo fallback) for each nearby spot.
7. **Filter by wave size** — keep spots whose current wave range overlaps the user's desired range.
8. **Display results** — table sorted by distance (default) or by condition rating.
9. **Send directions** — option to send a spot's details to a contact.

### Results Table

```
Surf spots with 2-3ft waves within 30mi of San Clemente, CA:

 #  Spot                  Waves    Conditions   Tide       Wind         Distance   Directions
──────────────────────────────────────────────────────────────────────────────────────────────────
 1  Trestles (Lowers)     2-3 ft   Fair-Good    Rising     Offshore     2.1 mi     https://maps.google.com/...
 2  T-Street              2-3 ft   Fair         Rising     Offshore     3.4 mi     https://maps.google.com/...
 3  San Onofre            2-3 ft   Fair         Rising     Onshore      5.8 mi     https://maps.google.com/...
```

### Sort Options

After results display:
```
Sort by: 1) Distance (current)  2) Best conditions first
```

"Best conditions" sorts by Surfline's rating: Epic > Good > Fair-Good > Fair > Poor > Flat.

---

## Feature 2: Manage Spot Regions

### Region Structure

Each region is a separate JSON file in `spots/`:

```json
[
  {
    "name": "Trestles (Lowers)",
    "lat": 33.3822,
    "lon": -117.5893,
    "surfline_id": "5842041f4e65fad6a7708890",
    "parking_lat": 33.3815,
    "parking_lon": -117.5880
  }
]
```

- `surfline_id` — optional. If present, uses Surfline API. If absent, falls back to Open-Meteo marine wave API.
- `parking_lat/parking_lon` — optional. If absent, defaults to the spot's lat/lon. Google Maps directions link points here.

### Menu

```
Spot Regions:
  1) SoCal (58 spots)
  2) Hawaii (12 spots)

  A) Add new region
  D) Delete a region
  S) Add/remove spots in a region
  B) Back
```

**Add region:** prompts for region name, creates empty JSON file, then prompts to add spots.

**Add spot:** prompts for name, lat, lon, surfline_id (or skip), parking coords (or "same").

**Delete region:** confirmation prompt, removes the JSON file.

**Remove spot from region:** numbered list of spots, pick one to remove.

---

## Feature 3: Manage Contacts

### Contact Structure (`contacts.json`)

```json
[
  {
    "name": "Jake",
    "phone": "9495551234",
    "carrier": "tmobile",
    "email": "jake@gmail.com"
  }
]
```

- `phone` + `carrier` — optional. Required for SMS.
- `email` — optional. Required for email.
- At least one of phone or email must be present.

### Menu

```
Contacts:
  1) Jake — 9495551234 (T-Mobile) / jake@gmail.com
  2) Sarah — sarah@gmail.com

  A) Add contact
  E) Edit contact
  D) Delete contact
  B) Back
```

### Send Flow (from Find Waves results)

```
Send directions? Enter spot # (or 'skip'): 2

Send to:
  1) Jake — 9495551234 (T-Mobile) / jake@gmail.com
  2) Sarah — sarah@gmail.com
  3) Enter new recipient

Choice: 1

How to send?
  1) Text (SMS)
  2) Email
  3) Both

Choice: 3
Directions to T-Street sent to Jake via text & email!

Save this contact for next time? (only shown for new recipients)
  Name (or 'skip'): Mike
  Phone # (or skip): 7145559876
  Carrier:
    1) T-Mobile       5) Metro by T-Mobile
    2) AT&T           6) Boost Mobile
    3) Verizon        7) US Cellular
    4) Cricket        8) Mint Mobile
  Carrier #: 2
  Email (or skip): mike@yahoo.com
  Saved "Mike"!
```

### SMS Message Format

```
T-Street — 2-3ft, Fair
Tide: Rising | Wind: Offshore
https://maps.google.com/dir/...
```

### Email Format

Subject: `Surf Alert: T-Street — 2-3ft`
Body: spot name, wave size, conditions, tide, wind, Google Maps directions link.

---

## Feature 4: Settings

### Config (`config.json`)

```json
{
  "gmail_address": "yourname@gmail.com",
  "gmail_app_password": "xxxx xxxx xxxx xxxx",
  "home_location": "92672",
  "default_region": "socal",
  "default_radius_miles": 30
}
```

### First-Run Setup

On first run, if `config.json` doesn't exist:
```
First-time setup:
  Gmail address: yourname@gmail.com
  App password: xxxx xxxx xxxx xxxx
  Home zip/city: 92672
  Saved!

  Test email send? (y/n): y
  Send test to: yourname@gmail.com
  Test message sent!
```

### Settings Menu

```
Settings:
  1) Update Gmail credentials
  2) Set home location (current: 92672)
  3) Set default region (current: SoCal)
  4) Set search radius (current: 30 miles)
  B) Back
```

---

## Data Sources

### Surfline Unofficial API (Primary)

- **Conditions endpoint:** `https://services.surfline.com/kbyg/spots/forecasts/conditions?spotId={id}&days=1`
  - Returns: wave height min/max, condition rating (human string), observation text
- **Wave endpoint:** `https://services.surfline.com/kbyg/spots/forecasts/wave?spotId={id}&days=1`
  - Returns: surf min/max height in feet, swell components
- **Tide endpoint:** `https://services.surfline.com/kbyg/spots/forecasts/tides?spotId={id}&days=1`
  - Returns: tide height over time, rising/falling status
- **Wind endpoint:** `https://services.surfline.com/kbyg/spots/forecasts/wind?spotId={id}&days=1`
  - Returns: wind speed, direction, onshore/offshore/cross-shore

All endpoints are unauthenticated GET requests returning JSON.

### Open-Meteo Marine Wave API (Fallback)

- **Endpoint:** `https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&current=wave_height,wave_direction,wave_period`
- Used for spots without a `surfline_id` (international/custom spots).
- Returns open-ocean swell data — less precise than Surfline for specific breaks but works globally.
- Free, no API key, no rate limits.

### Geocoding

- **Primary:** US Census geocoder `https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address={query}&benchmark=Public_AR_Current&format=json`
- **Fallback:** Open-Meteo geocoding `https://geocoding-api.open-meteo.com/v1/search?name={query}&count=1`
- Used to convert user's zip code or city name to lat/lon coordinates.

---

## Distance Calculation

Haversine formula to compute great-circle distance between user location and each spot. Standard implementation — no external library needed.

```
a = sin²(dlat/2) + cos(lat1) * cos(lat2) * sin²(dlon/2)
distance = 2 * R * atan2(sqrt(a), sqrt(1-a))
```

Where R = 3956 miles (Earth's radius).

Filter spots where distance <= configured radius BEFORE making any API calls.

---

## Google Maps Directions Link

Format: `https://www.google.com/maps/dir/?api=1&destination={parking_lat},{parking_lon}`

Uses parking coordinates when available, falls back to spot coordinates. Clickable in most terminals and in SMS/email.

---

## SMS Carrier Gateways

| #  | Carrier            | Gateway                    |
|----|--------------------|----------------------------|
| 1  | T-Mobile           | {number}@tmomail.net       |
| 2  | AT&T               | {number}@txt.att.net       |
| 3  | Verizon            | {number}@vtext.com         |
| 4  | Cricket            | {number}@sms.cricketwireless.net |
| 5  | Metro by T-Mobile  | {number}@mymetropcs.com    |
| 6  | Boost Mobile       | {number}@sms.myboostmobile.com |
| 7  | US Cellular        | {number}@email.uscc.net    |
| 8  | Mint Mobile        | {number}@mailmymobile.net  |

---

## Error Handling

- **Surfline API down/unreachable:** Show error message per spot, continue with remaining spots. Suggest trying again in a minute.
- **Geocoding fails:** Ask user to try a different format (zip vs city name) or enter lat/lon manually.
- **No spots match criteria:** Show message with count of spots checked and suggest broadening wave range or radius.
- **Gmail send fails:** Show error with common fix suggestions (check app password, check internet).
- **Invalid input:** Re-prompt with hint of expected format. Never crash on bad input.

---

## Pre-populated SoCal Spots

The `spots/socal.json` file ships with ~50-60 spots covering the SoCal coast from Ventura County to the Mexican border, including:

- **Ventura County:** Rincon, Ventura Point, C Street, Mondos
- **Santa Barbara/Malibu:** Zuma, Malibu (Surfrider), Topanga
- **South Bay/LA:** El Porto, Manhattan Beach, Hermosa, Torrance
- **Orange County:** Huntington Beach, Newport (Wedge, Blackies, 54th St), Salt Creek, Dana Point, Trestles (Uppers, Lowers, Middles, Cottons), San Onofre, T-Street, Doheny
- **San Diego County:** Oceanside, Cardiff Reef, Swamis, Black's Beach, La Jolla, Pacific Beach, Ocean Beach, Sunset Cliffs, Imperial Beach

Each spot includes name, lat/lon, Surfline spot ID, and parking coordinates.
