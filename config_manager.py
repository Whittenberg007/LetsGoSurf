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
