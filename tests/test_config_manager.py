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
