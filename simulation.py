"""Rebuilding every turn of a replay: positions, counts and violations.

The counting rules are those of Fly-in's ``ReservationTable``:

- A zone counts the drones in it at the end of the turn, waiting ones
  included; a drone on a connection is in no zone.
- A link counts the drones that use it during the turn, both directions
  combined. A move between zones uses it, entering a restricted zone
  uses it on the entry turn only, and landing or waiting does not.
"""

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum

from fly_map import Connection, FlyMap, Link, ZoneName, ZoneType
from replay import TurnRecord


@dataclass(frozen=True)
class InFlight:
    """A drone on a connection, halfway into a restricted zone.

    Attributes:
        connection: The connection the drone is on.
        dst: The zone it lands in on the next turn.
    """

    connection: Connection
    dst: ZoneName


type Position = ZoneName | InFlight


class ViolationKind(StrEnum):
    ZONE_FULL = "zone_full"
    LINK_FULL = "link_full"
    NO_CONNECTION = "no_connection"
    BLOCKED = "blocked"
    RESTRICTED_SKIPPED = "restricted_skipped"
    NOT_LANDED = "not_landed"
    NOT_RESTRICTED = "not_restricted"
    UNKNOWN_NAME = "unknown_name"
    UNKNOWN_DRONE = "unknown_drone"
    DUPLICATE_DRONE = "duplicate_drone"
    MOVED_AFTER_END = "moved_after_end"
    NOT_DELIVERED = "not_delivered"


@dataclass(frozen=True)
class Violation:
    """A broken rule, and what to draw in red for it.

    Attributes:
        kind: Which rule.
        message: One line explaining it, for the panel.
        zone: The zone to draw in red, if any.
        link: The link to draw in red, if any.
        drone: The drone to draw in red, if any.
    """

    kind: ViolationKind
    message: str
    zone: ZoneName | None = None
    link: Link | None = None
    drone: int | None = None


@dataclass
class TurnState:
    """Everything known at the end of one turn.

    Attributes:
        turn: The turn number; 0 is before any move.
        positions: Where each drone is, keyed by drone ID.
        zone_counts: Drones in each zone; zones with none may be absent.
        link_counts: Drones that used each link during the turn; unused
            links are absent.
        violations: Rules broken during the turn.
    """

    turn: int
    positions: dict[int, Position]
    zone_counts: dict[ZoneName, int]
    link_counts: dict[Link, int]
    violations: list[Violation]

    @property
    def used_links(self) -> set[Link]:
        """The links at least one drone used during the turn."""
        return {link for link, count in self.link_counts.items() if count}


def simulate(fly_map: FlyMap, records: list[TurnRecord]) -> list[TurnState]:
    """Replay the output turn by turn.

    Args:
        fly_map: The map the output was computed for.
        records: The output, one record per turn from turn 1.

    Returns:
        One state per turn, from turn 0 to the last turn.
    """
    positions: dict[int, Position] = {
        drone: fly_map.start for drone in range(1, fly_map.nb_drones + 1)
    }
    states = [_state(fly_map, 0, positions, Counter(), [])]
    for turn, record in enumerate(records, start=1):
        before = dict(positions)
        link_counts: Counter[Link] = Counter()
        violations: list[Violation] = []
        moved: set[int] = set()
        for move in record.moves:
            drone = move.drone
            if drone not in before:
                violations.append(
                    Violation(K.UNKNOWN_DRONE, f"D{drone}: unknown drone")
                )
                continue
            if drone in moved:
                violations.append(
                    Violation(
                        K.DUPLICATE_DRONE, f"D{drone}: appears twice",
                        drone=drone,
                    )
                )
                continue
            moved.add(drone)
            new = _resolve(fly_map, before[drone], move.name)
            if new is None:
                violations.append(
                    Violation(
                        K.UNKNOWN_NAME,
                        f"D{drone}: unknown zone or connection {move.name}",
                        drone=drone,
                    )
                )
                continue
            violations += _check_move(fly_map, drone, before[drone], new)
            positions[drone] = new
            used = _used_link(fly_map, before[drone], new)
            if used is not None:
                link_counts[used] += 1
        for drone, position in before.items():
            if isinstance(position, InFlight) and drone not in moved:
                violations.append(_not_landed(drone, position))
        states.append(
            _state(fly_map, turn, positions, link_counts, violations)
        )
    last = states[-1]
    for drone, position in last.positions.items():
        if position != fly_map.end:
            last.violations.append(
                Violation(
                    K.NOT_DELIVERED, f"D{drone}: did not reach end",
                    drone=drone,
                )
            )
    return states


K = ViolationKind


def _state(
    fly_map: FlyMap,
    turn: int,
    positions: dict[int, Position],
    link_counts: Counter[Link],
    violations: list[Violation],
) -> TurnState:
    """Build a turn's state, adding the capacity violations."""
    zone_counts = Counter(
        position for position in positions.values()
        if isinstance(position, str)
    )
    for zone, count in zone_counts.items():
        limit = fly_map.zones[zone].max_drones
        if count > limit:
            violations.append(
                Violation(
                    K.ZONE_FULL,
                    f"{zone}: {count}/{limit} (over max_drones)",
                    zone=zone,
                )
            )
    for link, count in link_counts.items():
        a, b = sorted(link)
        connection = fly_map.connection_between(a, b)
        assert connection is not None  # only real links are counted
        limit = connection.max_link_capacity
        if count > limit:
            violations.append(
                Violation(
                    K.LINK_FULL,
                    f"{connection.name}: {count}/{limit} "
                    "(over max_link_capacity)",
                    link=link,
                )
            )
    return TurnState(
        turn, dict(positions), dict(zone_counts), dict(link_counts),
        violations,
    )


def _not_landed(drone: int, flight: InFlight) -> Violation:
    """The violation for a drone that did not land in ``flight.dst``."""
    return Violation(
        K.NOT_LANDED, f"D{drone}: did not land in {flight.dst}", drone=drone
    )


def _check_move(
    fly_map: FlyMap, drone: int, before: Position, after: Position
) -> list[Violation]:
    """The rules one move breaks.

    Args:
        fly_map: The map.
        drone: The drone's ID.
        before: Where it was at the end of the previous turn.
        after: Where the output says it is now.

    Returns:
        The violations, possibly none.
    """
    if isinstance(before, InFlight):
        return [] if after == before.dst else [_not_landed(drone, before)]

    found: list[Violation] = []
    if before == fly_map.end and after != before:
        found.append(
            Violation(
                K.MOVED_AFTER_END, f"D{drone}: moved after reaching end",
                drone=drone,
            )
        )
    if isinstance(after, InFlight):
        connection = after.connection
        if before not in (connection.a, connection.b):
            found.append(
                Violation(
                    K.NO_CONNECTION,
                    f"D{drone}: no connection {before}-{after.dst}",
                    drone=drone,
                )
            )
        if fly_map.zones[after.dst].zone_type is not ZoneType.RESTRICTED:
            found.append(
                Violation(
                    K.NOT_RESTRICTED,
                    f"D{drone}: {connection.name} does not lead to a "
                    "restricted zone",
                    link=connection.link,
                    drone=drone,
                )
            )
        return found

    if after == before:
        return found
    if fly_map.connection_between(before, after) is None:
        found.append(
            Violation(
                K.NO_CONNECTION, f"D{drone}: no connection {before}-{after}",
                drone=drone,
            )
        )
    zone_type = fly_map.zones[after].zone_type
    if zone_type is ZoneType.BLOCKED:
        found.append(
            Violation(
                K.BLOCKED, f"D{drone}: entered blocked zone {after}",
                zone=after, drone=drone,
            )
        )
    elif zone_type is ZoneType.RESTRICTED:
        found.append(
            Violation(
                K.RESTRICTED_SKIPPED,
                f"D{drone}: entered restricted zone {after} in one turn",
                zone=after, drone=drone,
            )
        )
    return found


def _resolve(
    fly_map: FlyMap, before: Position, name: str
) -> Position | None:
    """The position a move's name refers to.

    Args:
        fly_map: The map.
        before: Where the drone was before the move.
        name: A zone name or a connection name from the output.

    Returns:
        The zone, or the drone on the connection; None if ``name``
        names neither.
    """
    if name in fly_map.zones:
        return name
    connection = fly_map.connection_named(name)
    if connection is None:
        return None
    ends = (connection.a, connection.b)
    if before in ends:
        dst = connection.b if before == connection.a else connection.a
    else:
        restricted = [
            end for end in ends
            if fly_map.zones[end].zone_type is ZoneType.RESTRICTED
        ]
        dst = restricted[0] if restricted else connection.b
    return InFlight(connection, dst)


def _used_link(
    fly_map: FlyMap, before: Position, after: Position
) -> Link | None:
    """The link a move uses during its turn, if any."""
    if isinstance(after, InFlight):
        return after.connection.link
    if isinstance(before, InFlight) or before == after:
        return None
    connection = fly_map.connection_between(before, after)
    return connection.link if connection is not None else None
