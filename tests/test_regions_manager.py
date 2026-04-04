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
