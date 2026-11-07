"""Small maps and outputs for the simulation tests."""

from fly_map import Connection, FlyMap, Zone, ZoneName, ZoneType
from replay import TurnRecord, parse_line

N = ZoneType.NORMAL
B = ZoneType.BLOCKED
R = ZoneType.RESTRICTED


def make_map(
    hubs: dict[ZoneName, ZoneType],
    links: list[str],
    nb_drones: int = 2,
    capacities: dict[ZoneName, int] | None = None,
    link_capacities: dict[str, int] | None = None,
) -> FlyMap:
    """Build a FlyMap with start ``s``, end ``e`` and the given hubs.

    Hubs hold one drone unless ``capacities`` says otherwise; start and
    end hold ``nb_drones``. Links are ``"a-b"`` names with capacity 1
    unless ``link_capacities`` says otherwise.
    """
    capacities = capacities or {}
    link_capacities = link_capacities or {}
    zone_types = {"s": N, **hubs, "e": N}
    zones = {
        name: Zone(
            name,
            i,
            0,
            zone_type,
            None,
            nb_drones if name in ("s", "e") else capacities.get(name, 1),
        )
        for i, (name, zone_type) in enumerate(zone_types.items())
    }
    connections = []
    for link in links:
        a, b = link.split("-")
        connections.append(Connection(a, b, link_capacities.get(link, 1)))
    return FlyMap(nb_drones, "s", "e", zones, connections)


def turns(*lines: str) -> list[TurnRecord]:
    """Parse output lines; the first one is turn 1."""
    return [
        parse_line(line_no, line)
        for line_no, line in enumerate(lines, start=1)
    ]


def link(a: ZoneName, b: ZoneName) -> frozenset[ZoneName]:
    """The link between two zones."""
    return frozenset((a, b))
