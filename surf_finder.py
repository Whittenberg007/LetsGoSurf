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


def directions_url(spot: dict, device: str = "android") -> str:
    """Generate maps directions URL. Uses Apple Maps for iPhone, Google Maps for Android."""
    lat = spot.get("parking_lat", spot["lat"])
    lon = spot.get("parking_lon", spot["lon"])
    if device == "iphone":
        return f"https://maps.apple.com/?daddr={lat},{lon}"
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

    # Step 5: Query conditions for ALL nearby spots
    all_conditions = []
    for spot, dist in nearby:
        if spot.get("surfline_id"):
            conditions = get_surfline_conditions(spot["surfline_id"])
        else:
            conditions = get_openmeteo_conditions(spot["lat"], spot["lon"])

        if conditions:
            all_conditions.append((spot, conditions, dist))

    if not all_conditions:
        print(f"\n  Could not fetch conditions for any spots near {location_name}.")
        print("  Surfline may be down. Try again in a minute.")
        return contacts

    # Filter to matching wave size
    results = [
        (spot, cond, dist) for spot, cond, dist in all_conditions
        if ranges_overlap(desired_min, desired_max, cond["wave_min"], cond["wave_max"])
    ]

    if not results:
        # Show what IS out there so the user can adjust
        all_conditions.sort(key=lambda x: x[2])
        print(f"\n  No spots with exactly {wave_input}ft waves near {location_name}.")
        print(f"  Here's what's currently out there ({len(all_conditions)} spots):\n")

        header = f"  {'#':<4}{'Spot':<26}{'Waves':<10}{'Conditions':<14}{'Tide':<10}{'Wind':<12}{'Parking':<18}{'Distance':<10}Directions"
        print(header)
        print("  " + "-" * (len(header) - 2))

        for i, (spot, cond, dist) in enumerate(all_conditions):
            waves = f"{cond['wave_min']}-{cond['wave_max']} ft"
            url = directions_url(spot)
            parking = spot.get("parking_cost", "Unknown")
            print(f"  {i+1:<4}{spot['name']:<26}{waves:<10}{cond['condition_rating']:<14}{cond['tide_trend']:<10}{cond['wind_direction_type']:<12}{parking:<18}{dist:<10.1f}{url}")

        # Suggest wave ranges that have results
        wave_sizes = set()
        for _, cond, _ in all_conditions:
            low = int(cond["wave_min"])
            high = max(low + 1, int(cond["wave_max"]) + 1)
            wave_sizes.add(f"{low}-{high}")
        if wave_sizes:
            print(f"\n  Try these wave ranges: {', '.join(sorted(wave_sizes))}ft")

        # Still allow sending directions from the full list
        results = all_conditions

    else:
        # Sort matches by distance (default)
        results.sort(key=lambda x: x[2])

    # Step 6: Display results (only if we had matches — "no matches" already displayed above)
    has_exact_matches = any(
        ranges_overlap(desired_min, desired_max, cond["wave_min"], cond["wave_max"])
        for _, cond, _ in results
    )
    if has_exact_matches:
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
    header = f"  {'#':<4}{'Spot':<26}{'Waves':<10}{'Conditions':<14}{'Tide':<10}{'Wind':<12}{'Parking':<18}{'Distance':<10}Directions"
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
    print("\n  Send directions?")
    print("    A) Send the full list")
    print("    #) Send a specific spot (enter spot number)")
    print("    S) Skip")
    send_choice = input("\n  Choice: ").strip()
    if send_choice.lower() in ("s", "skip", ""):
        return contacts

    # Determine what to send
    if send_choice.lower() == "a":
        # Build combined message for full list
        spots_to_send = results
    else:
        try:
            spot_idx = int(send_choice) - 1
            if not (0 <= spot_idx < len(results)):
                print(f"  Invalid spot number. Enter 1-{len(results)}.")
                return contacts
            spots_to_send = [results[spot_idx]]
        except ValueError:
            print(f"  Invalid choice. Enter A, 1-{len(results)}, or S.")
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

    gmail = config.get("gmail_address", "")
    gmail_pw = config.get("gmail_app_password", "")

    if not gmail or not gmail_pw:
        print("  Gmail not configured. Go to Settings first.")
        return contacts

    # Build message(s) using recipient's device preference for maps links
    device = contact.get("device", "android")

    if len(spots_to_send) == 1:
        spot, cond, dist = spots_to_send[0]
        url = directions_url(spot, device)
        subject, body = build_spot_message(spot, cond, url)
        send_label = spot["name"]
    else:
        # Build one compiled message for the full list
        subject = f"Surf Report: {len(spots_to_send)} spots near {location_name}"
        lines = [f"Surf spots near {location_name}:"]
        lines.append("")
        for i, (spot, cond, dist) in enumerate(spots_to_send):
            url = directions_url(spot, device)
            parking = spot.get("parking_cost", "Unknown")
            lines.append(f"{i+1}. {spot['name']} — {cond['wave_min']}-{cond['wave_max']}ft, {cond['condition_rating']}")
            lines.append(f"   Tide: {cond['tide_trend']} | Wind: {cond['wind_direction_type']}")
            lines.append(f"   Parking: {parking} | {dist:.1f}mi away")
            lines.append(f"   {url}")
            lines.append("")
        body = "\n".join(lines)
        send_label = f"{len(spots_to_send)} spots"

    # Send one single message (not individual per spot)
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
        print(f"\n  {send_label} sent to {contact['name']} via {method_name}!")

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
            print("\n  Hang loose!\n")
            break
        else:
            print("  Invalid choice. Enter 1-5.")


if __name__ == "__main__":
    main()
