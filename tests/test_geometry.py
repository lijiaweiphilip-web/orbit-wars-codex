from orbitwars.geometry import angle_between, distance, estimate_eta


def test_geometry_helpers():
    assert round(distance(0, 0, 3, 4), 4) == 5.0
    assert round(angle_between(0, 0, 1, 0), 4) == 0.0
    assert estimate_eta(10, 10, 6.0) >= 1
