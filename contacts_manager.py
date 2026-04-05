import json
import os

CARRIERS = {
    "tmobile": "{number}@tmomail.net",
    "att": "{number}@txt.att.net",
    "verizon": "{number}@vtext.com",
    "spectrum": "{number}@vtext.com",
    "cricket": "{number}@sms.cricketwireless.net",
    "metro": "{number}@mymetropcs.com",
    "boost": "{number}@sms.myboostmobile.com",
    "uscellular": "{number}@email.uscc.net",
    "mint": "{number}@mailmymobile.net",
    "googlefi": "{number}@msg.fi.google.com",
    "visible": "{number}@vzwpix.com",
    "xfinity": "{number}@vtext.com",
}

CARRIER_DISPLAY = {
    "tmobile": "T-Mobile",
    "att": "AT&T",
    "verizon": "Verizon",
    "spectrum": "Spectrum Mobile",
    "cricket": "Cricket",
    "metro": "Metro by T-Mobile",
    "boost": "Boost Mobile",
    "uscellular": "US Cellular",
    "mint": "Mint Mobile",
    "googlefi": "Google Fi",
    "visible": "Visible",
    "xfinity": "Xfinity Mobile",
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
    if carrier.startswith("custom:"):
        # Custom gateway stored as "custom:@domain.com"
        gateway = carrier.replace("custom:", "")
        return f"{phone}{gateway}"
    template = CARRIERS.get(carrier, "")
    return template.replace("{number}", phone)


DEVICE_TYPES = {"iphone": "iPhone", "android": "Android"}


def prompt_device() -> str:
    """Display device menu and return device key."""
    print("    Device:")
    print("      1) iPhone (Apple Maps)")
    print("      2) Android (Google Maps)")
    while True:
        try:
            choice = int(input("    Device #: ").strip())
            if choice == 1:
                return "iphone"
            elif choice == 2:
                return "android"
        except ValueError:
            pass
        print("    Invalid choice. Try again.")


def display_contact(contact: dict) -> str:
    """Format a contact for display."""
    parts = [contact["name"]]
    if contact.get("phone"):
        carrier_key = contact.get("carrier", "")
        if carrier_key.startswith("custom:"):
            carrier_name = f"Custom ({carrier_key.replace('custom:', '')})"
        else:
            carrier_name = CARRIER_DISPLAY.get(carrier_key, carrier_key)
        device_name = DEVICE_TYPES.get(contact.get("device", ""), "")
        device_str = f", {device_name}" if device_name else ""
        parts.append(f"{contact['phone']} ({carrier_name}{device_str})")
    if contact.get("email"):
        parts.append(contact["email"])
    return " — ".join(parts[1:]) if len(parts) > 1 else parts[0]


def prompt_carrier() -> str:
    """Display carrier menu and return carrier key. Returns 'custom:gateway@domain' for manual entry."""
    print("    Carrier:")
    for i, key in enumerate(CARRIER_KEYS):
        col1 = f"      {i + 1}) {CARRIER_DISPLAY[key]}"
        if i % 2 == 0 and i + 1 < len(CARRIER_KEYS):
            col2 = f"{i + 2}) {CARRIER_DISPLAY[CARRIER_KEYS[i + 1]]}"
            print(f"{col1:<30}{col2}")
        elif i % 2 == 0:
            print(col1)
    other_num = len(CARRIER_KEYS) + 1
    print(f"      {other_num}) Other (enter SMS gateway manually)")
    while True:
        try:
            choice = int(input("    Carrier #: ").strip())
            if 1 <= choice <= len(CARRIER_KEYS):
                return CARRIER_KEYS[choice - 1]
            elif choice == other_num:
                print("    Enter the SMS email gateway for your carrier.")
                print("    Format: @domain.com (e.g., @txt.att.net)")
                print("    Google your carrier name + 'SMS email gateway' to find it.")
                gateway = input("    Gateway (e.g., @txt.att.net): ").strip()
                if not gateway.startswith("@"):
                    gateway = "@" + gateway
                return f"custom:{gateway}"
        except ValueError:
            pass
        print("    Invalid choice. Try again.")


def prompt_new_contact() -> dict:
    """Interactive prompt to create a new contact."""
    name = input("    Name: ").strip()
    phone = input("    Phone # (or skip): ").strip()
    carrier = ""
    device = ""
    if phone and phone.lower() != "skip":
        carrier = prompt_carrier()
        device = prompt_device()
    else:
        phone = ""
    email = input("    Email (or skip): ").strip()
    if email.lower() == "skip":
        email = ""
    return {"name": name, "phone": phone, "carrier": carrier, "device": device, "email": email}


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
                        contacts[idx]["device"] = prompt_device()
                    else:
                        # Allow changing device without changing phone
                        current_device = DEVICE_TYPES.get(contacts[idx].get("device", ""), "not set")
                        change_device = input(f"    Change device? (current: {current_device}) (y/n): ").strip().lower()
                        if change_device == "y":
                            contacts[idx]["device"] = prompt_device()
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
