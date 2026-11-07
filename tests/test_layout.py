"""Tests for layout.py and colors.py."""

import math

from colors import UNKNOWN_ZONE, zone_rgb
from fly_map import Connection, FlyMap, Zone
from layout import MapLayout, lerp, slot_offsets
from simulation import InFlight


def grid_map(*coords: tuple[int, int]) -> FlyMap:
    """A map with one zone per coordinate, named z0, z1, ..."""
    zones = {
        f"z{i}": Zone(f"z{i}", x, y) for i, (x, y) in enumerate(coords)
    }
    names = list(zones)
    return FlyMap(1, names[0], names[-1], zones, [])


def test_fits_and_keeps_aspect() -> None:
    """L1: zones fill the area inside the margin, centred on x."""
    layout = MapLayout(grid_map((0, 0), (3, 2)), 0, 0, 800, 400, margin=60)
    assert layout.zone_point("z0") == (190.0, 60.0)
    assert layout.zone_point("z1") == (610.0, 340.0)


def test_single_point_is_centred() -> None:
    """L2: one zone, or zones on one spot, sit in the middle."""
    single = MapLayout(grid_map((5, 5)), 10, 20, 800, 400)
    assert single.zone_point("z0") == (410.0, 220.0)
    same = MapLayout(grid_map((1, 1), (1, 1)), 0, 0, 800, 400)
    assert same.zone_point("z1") == (400.0, 200.0)


def test_y_grows_downwards() -> None:
    """L3: a larger y in the map is lower on screen."""
    layout = MapLayout(grid_map((0, 0), (0, 1)), 0, 0, 800, 400)
    assert layout.zone_point("z1")[1] > layout.zone_point("z0")[1]


def test_in_flight_is_midpoint() -> None:
    """L4: a drone on a connection is drawn halfway along it."""
    fly_map = grid_map((0, 0), (2, 0))
    layout = MapLayout(fly_map, 0, 0, 800, 400)
    flight = InFlight(Connection("z0", "z1"), "z1")
    (x0, y0), (x1, y1) = layout.zone_point("z0"), layout.zone_point("z1")
    assert layout.position_point(flight) == ((x0 + x1) / 2, (y0 + y1) / 2)
    assert layout.position_point("z0") == (x0, y0)


def test_lerp() -> None:
    """L4a: lerp goes in a straight line from a to b."""
    assert lerp((0, 0), (10, 20), 0.25) == (2.5, 5.0)


def test_slot_offsets() -> None:
    """L5: one drone sits in the middle; several form a circle."""
    assert slot_offsets(1, 10) == [(0.0, 0.0)]
    offsets = slot_offsets(4, 10)
    assert len(set(offsets)) == 4
    for dx, dy in offsets:
        assert math.isclose(math.hypot(dx, dy), 10)


def test_zone_rgb() -> None:
    """L6: color names ignore case; unknown or no color is gray."""
    assert zone_rgb("RED") == zone_rgb("red") == (255, 60, 60)
    assert zone_rgb(None) == zone_rgb("rainbow") == UNKNOWN_ZONE


def test_tiny_area() -> None:
    """L7: an area smaller than the margins does not fail."""
    layout = MapLayout(grid_map((0, 0), (3, 2)), 0, 0, 50, 30, margin=60)
    assert layout.zone_point("z0") == (25.0, 15.0)
    assert layout.zone_point("z1") == (25.0, 15.0)
