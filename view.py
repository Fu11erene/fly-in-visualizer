"""Drawing the map, the counts and the drones."""

import math
from collections import defaultdict

import pygame

from colors import (
    BACKGROUND,
    DIM_TEXT,
    ERROR,
    HIGHLIGHT,
    LINK,
    TEXT,
    zone_rgb,
)
from fly_map import FlyMap, ZoneType
from layout import MapLayout, Point, lerp, slot_offsets
from replay import RGB
from simulation import Position, TurnState

DRONE_RADIUS = 9
MAX_SPREAD = 6
"""More drones than this on one spot are drawn as one counted dot."""
COMPACT_SCALE = 80
"""Below this many pixels per map unit, labels are only shown on hover
or when something is in use."""


def zone_radius(layout: MapLayout) -> float:
    """Zone size, so that neighbouring zones do not overlap."""
    if layout.scale == 0:
        return 18.0
    return max(8.0, min(18.0, layout.scale * 0.22))


def draw_map(
    surface: pygame.Surface,
    layout: MapLayout,
    fly_map: FlyMap,
    before: TurnState,
    after: TurnState,
    alpha: float,
    font: pygame.font.Font,
    hover: tuple[int, int] | None = None,
) -> None:
    """Draw the map during the move from ``before`` to ``after``.

    Highlights, counts and red marks are those of ``after``.

    Args:
        surface: Where to draw.
        layout: Where each zone goes on ``surface``.
        fly_map: The map.
        before: The state the move starts from.
        after: The state the move leads to.
        alpha: How far into the move, from 0 to 1; at 0 only ``after``
            is drawn.
        font: Font for names, counts and drone IDs.
        hover: Mouse position; the zone under it gets its full label
            even when the map is too dense for labels.
    """
    if alpha == 0:
        before = after
    red_links = {v.link for v in after.violations if v.link is not None}
    red_zones = {v.zone for v in after.violations if v.zone is not None}
    red_drones = {v.drone for v in after.violations if v.drone is not None}
    compact = 0 < layout.scale < COMPACT_SCALE
    _draw_links(surface, layout, fly_map, after, red_links, font, compact)
    _draw_zones(surface, layout, fly_map, after, red_zones, font, compact)
    _draw_drones(surface, layout, before, after, alpha, red_drones, font)
    if hover is not None:
        _draw_hover(surface, layout, fly_map, after, font, hover)


def _text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    color: RGB,
    center: Point,
) -> None:
    """Draw ``text`` centred on ``center``."""
    image = font.render(text, True, color)
    rect = image.get_rect(center=(int(center[0]), int(center[1])))
    surface.blit(image, rect)


def _draw_links(
    surface: pygame.Surface,
    layout: MapLayout,
    fly_map: FlyMap,
    after: TurnState,
    red_links: set[frozenset[str]],
    font: pygame.font.Font,
    compact: bool,
) -> None:
    """Draw every connection with its ``used/capacity`` label.

    In compact mode only links in use get a label.
    """
    used = after.used_links
    for connection in fly_map.connections:
        a = layout.zone_point(connection.a)
        b = layout.zone_point(connection.b)
        link = connection.link
        if link in red_links:
            color, width = ERROR, 6
        elif link in used:
            color, width = HIGHLIGHT, 6
        else:
            color, width = LINK, 3
        pygame.draw.line(surface, color, a, b, width)

        # Put the label beside the midpoint, where flying drones are.
        mid = lerp(a, b, 0.5)
        length = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
        nx, ny = -(b[1] - a[1]) / length, (b[0] - a[0]) / length
        count = after.link_counts.get(link, 0)
        if compact and count == 0:
            continue
        label_color = color if color != LINK else DIM_TEXT
        _text(
            surface,
            font,
            f"{count}/{connection.max_link_capacity}",
            label_color,
            (mid[0] + nx * 16, mid[1] + ny * 16),
        )


def _draw_zones(
    surface: pygame.Surface,
    layout: MapLayout,
    fly_map: FlyMap,
    after: TurnState,
    red_zones: set[str],
    font: pygame.font.Font,
    compact: bool,
) -> None:
    """Draw every zone with its name and ``used/max_drones`` label.

    In compact mode names are left out, and only zones holding drones
    get their count.
    """
    radius = zone_radius(layout)
    line = font.get_linesize()
    for zone in fly_map.zones.values():
        x, y = layout.zone_point(zone.name)
        pygame.draw.circle(surface, zone_rgb(zone.color), (x, y), radius)
        if zone.zone_type is ZoneType.BLOCKED:
            d = radius * 0.6
            for sign in (1, -1):
                pygame.draw.line(
                    surface, BACKGROUND, (x - d, y - sign * d),
                    (x + d, y + sign * d), 3,
                )
        red = zone.name in red_zones
        if red:
            pygame.draw.circle(surface, ERROR, (x, y), radius + 4, 4)
        count = after.zone_counts.get(zone.name, 0)
        if compact:
            if count or red:
                _text(
                    surface,
                    font,
                    f"{count}/{zone.max_drones}",
                    ERROR if red else DIM_TEXT,
                    (x, y + radius + line * 0.7),
                )
            continue
        _text(surface, font, zone.name, TEXT, (x, y + radius + line * 0.7))
        _text(
            surface,
            font,
            f"{count}/{zone.max_drones}",
            ERROR if red else DIM_TEXT,
            (x, y + radius + line * 1.7),
        )


def _groups(positions: dict[int, Position]) -> dict[Position, list[int]]:
    """The drones on each spot, in ID order."""
    groups: dict[Position, list[int]] = defaultdict(list)
    for drone, position in sorted(positions.items()):
        groups[position].append(drone)
    return groups


def _spread(
    layout: MapLayout, positions: dict[int, Position]
) -> dict[int, Point]:
    """Where each drone is drawn, apart from drones on the same spot.

    Drones on a crowded spot (more than ``MAX_SPREAD``) all go to its
    centre, where they are drawn as one counted dot.
    """
    points: dict[int, Point] = {}
    for position, drones in _groups(positions).items():
        cx, cy = layout.position_point(position)
        count = len(drones) if len(drones) <= MAX_SPREAD else 1
        offsets = slot_offsets(count, DRONE_RADIUS * 1.6) * len(drones)
        for drone, (dx, dy) in zip(drones, offsets, strict=False):
            points[drone] = (cx + dx, cy + dy)
    return points


def _draw_drones(
    surface: pygame.Surface,
    layout: MapLayout,
    before: TurnState,
    after: TurnState,
    alpha: float,
    red_drones: set[int],
    font: pygame.font.Font,
) -> None:
    """Draw each drone as a numbered white dot, moving along its move."""
    start = _spread(layout, before.positions)
    end = _spread(layout, after.positions)
    crowds = {
        position: drones
        for position, drones in _groups(after.positions).items()
        if len(drones) > MAX_SPREAD
    }
    crowded = {drone for drones in crowds.values() for drone in drones}
    if alpha == 0:
        for position, drones in crowds.items():
            x, y = layout.position_point(position)
            red = any(drone in red_drones for drone in drones)
            radius = DRONE_RADIUS * 1.6
            if red:
                pygame.draw.circle(surface, ERROR, (x, y), radius + 3)
            pygame.draw.circle(surface, (255, 255, 255), (x, y), radius)
            _text(surface, font, f"x{len(drones)}", (0, 0, 0), (x, y))
    for drone in sorted(after.positions):
        if alpha == 0 and drone in crowded:
            continue
        x, y = lerp(start[drone], end[drone], alpha)
        if drone in red_drones:
            pygame.draw.circle(surface, ERROR, (x, y), DRONE_RADIUS + 3)
        pygame.draw.circle(surface, (255, 255, 255), (x, y), DRONE_RADIUS)
        _text(surface, font, str(drone), (0, 0, 0), (x, y))


def _draw_hover(
    surface: pygame.Surface,
    layout: MapLayout,
    fly_map: FlyMap,
    after: TurnState,
    font: pygame.font.Font,
    hover: tuple[int, int],
) -> None:
    """Label the zone under the mouse with its name and count."""
    radius = zone_radius(layout) + 6
    for zone in fly_map.zones.values():
        x, y = layout.zone_point(zone.name)
        if math.hypot(hover[0] - x, hover[1] - y) > radius:
            continue
        count = after.zone_counts.get(zone.name, 0)
        text = f"{zone.name}  {count}/{zone.max_drones}  ({zone.zone_type})"
        image = font.render(text, True, TEXT)
        box = image.get_rect(midbottom=(int(x), int(y - radius - 4)))
        box.clamp_ip(surface.get_rect())
        pygame.draw.rect(surface, BACKGROUND, box.inflate(10, 6))
        pygame.draw.rect(surface, DIM_TEXT, box.inflate(10, 6), 1)
        surface.blit(image, box)
        return
