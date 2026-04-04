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
