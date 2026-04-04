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
