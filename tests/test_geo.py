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
