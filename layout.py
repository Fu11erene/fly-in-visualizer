"""Placing the map on screen."""

import math

from fly_map import FlyMap, ZoneName
from simulation import InFlight, Position

type Point = tuple[float, float]


def lerp(a: Point, b: Point, t: float) -> Point:
    """The point a fraction ``t`` of the way from ``a`` to ``b``."""
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def slot_offsets(count: int, radius: float) -> list[Point]:
    """Offsets that keep drones on the same spot apart.

    Args:
        count: Number of drones on the spot.
        radius: Distance from the spot for two drones or more.

    Returns:
        ``count`` offsets: the origin for one drone, otherwise evenly
        spaced points on a circle of ``radius``.
    """
    if count <= 1:
        return [(0.0, 0.0)] * count
    return [
        (
            radius * math.cos(2 * math.pi * i / count - math.pi / 2),
            radius * math.sin(2 * math.pi * i / count - math.pi / 2),
        )
        for i in range(count)
    ]


class MapLayout:
    """Scales the map's coordinates into a screen rectangle.

    The aspect ratio is kept and the map is centred. A larger ``y`` is
    lower on screen, as in screen coordinates.
    """

    def __init__(
        self,
        fly_map: FlyMap,
        left: float,
        top: float,
        width: float,
        height: float,
        margin: float = 60,
    ) -> None:
        """Fit every zone of ``fly_map`` inside the rectangle.

        Args:
            fly_map: The map.
            left: Left edge of the rectangle.
            top: Top edge of the rectangle.
            width: Width of the rectangle.
            height: Height of the rectangle.
            margin: Space kept free on each side; shrunk when the
                rectangle is too small for it.
        """
        self._fly_map = fly_map
        margin = max(0.0, min(margin, width / 2, height / 2))
        inner_w = width - 2 * margin
        inner_h = height - 2 * margin
        xs = [zone.x for zone in fly_map.zones.values()]
        ys = [zone.y for zone in fly_map.zones.values()]
        self._min_x, self._min_y = min(xs), min(ys)
        span_x, span_y = max(xs) - self._min_x, max(ys) - self._min_y
        scales = [
            size / span
            for size, span in ((inner_w, span_x), (inner_h, span_y))
            if span
        ]
        self._scale = min(scales) if scales else 0.0
        self._left = left + margin + (inner_w - span_x * self._scale) / 2
        self._top = top + margin + (inner_h - span_y * self._scale) / 2

    @property
    def scale(self) -> float:
        """Screen pixels per map unit; 0 when every zone is on one spot."""
        return self._scale

    def zone_point(self, name: ZoneName) -> Point:
        """Where a zone is drawn."""
        zone = self._fly_map.zones[name]
        return (
            self._left + (zone.x - self._min_x) * self._scale,
            self._top + (zone.y - self._min_y) * self._scale,
        )

    def position_point(self, position: Position) -> Point:
        """Where a drone at ``position`` is drawn, before spreading.

        A drone on a connection is drawn at the connection's midpoint.
        """
        if isinstance(position, InFlight):
            connection = position.connection
            return lerp(
                self.zone_point(connection.a),
                self.zone_point(connection.b),
                0.5,
            )
        return self.zone_point(position)
