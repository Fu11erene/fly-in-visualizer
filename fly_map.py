"""Reading Fly-in map files.

The maps are expected to have been validated by Fly-in already, so this
parser only checks what it needs to draw and replay the map.
"""

from dataclasses import dataclass
from enum import StrEnum

type ZoneName = str

type Link = frozenset[ZoneName]
"""Unordered pair of zone names; ``a-b`` and ``b-a`` are the same link."""

ZONE_KEYS = ("start_hub", "hub", "end_hub")


class ZoneType(StrEnum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


@dataclass(frozen=True)
class Zone:
    """A zone of the map.

    Attributes:
        name: Unique name of the zone; never contains ``-``.
        x: X coordinate from the map file.
        y: Y coordinate from the map file.
        zone_type: The zone's type.
        color: Color name from the map file, or None.
        max_drones: Drones the zone holds at the end of a turn;
            ``nb_drones`` for start and end.
    """

    name: ZoneName
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = 1


@dataclass(frozen=True)
class Connection:
    """A connection between two zones, usable in both directions.

    Attributes:
        a: The zone written first in the map file.
        b: The zone written second.
        max_link_capacity: Drones that can use it during one turn, both
            directions combined.
    """

    a: ZoneName
    b: ZoneName
    max_link_capacity: int = 1

    @property
    def link(self) -> Link:
        """The unordered pair ``{a, b}``."""
        return frozenset((self.a, self.b))

    @property
    def name(self) -> str:
        """The connection as written in the map file, ``a-b``."""
        return f"{self.a}-{self.b}"


@dataclass(frozen=True)
class FlyMap:
    """A parsed map file.

    Attributes:
        nb_drones: Number of drones, all starting at ``start``.
        start: Name of the start zone.
        end: Name of the end zone.
        zones: Every zone, keyed by name, in file order.
        connections: Every connection, in file order.
    """

    nb_drones: int
    start: ZoneName
    end: ZoneName
    zones: dict[ZoneName, Zone]
    connections: list[Connection]

    def connection_between(
        self, a: ZoneName, b: ZoneName
    ) -> Connection | None:
        """The connection joining two zones, in either direction.

        Args:
            a: One zone.
            b: The other zone.

        Returns:
            The connection, or None if the zones are not connected.
        """
        link = frozenset((a, b))
        for connection in self.connections:
            if connection.link == link:
                return connection
        return None

    def connection_named(self, name: str) -> Connection | None:
        """The connection written as ``a-b`` or ``b-a``.

        Args:
            name: A connection name from the output, e.g. ``s-r``.

        Returns:
            The connection, or None if ``name`` is not ``<a>-<b>`` or
            names no connection.
        """
        parts = name.split("-")
        if len(parts) != 2:
            return None
        return self.connection_between(parts[0], parts[1])


class MapFileError(Exception):
    """Error in a map file, reported with its line number."""

    def __init__(self, line_no: int, message: str) -> None:
        """Build the message as ``line <line_no>: <message>``.

        Args:
            line_no: 1-based line number, or 0 for the whole file.
            message: What is wrong.
        """
        super().__init__(f"line {line_no}: {message}")


def parse_map(path: str) -> FlyMap:
    """Read a map file.

    Args:
        path: Path to the map file.

    Returns:
        The map.

    Raises:
        OSError: If the file cannot be read.
        MapFileError: If a line cannot be read, a zone or connection is
            defined twice, a connection names an undefined zone or
            joins a zone to itself, or nb_drones, start_hub or end_hub
            is missing.
    """
    nb_drones: int | None = None
    start: ZoneName | None = None
    end: ZoneName | None = None
    zones: dict[ZoneName, Zone] = {}
    connections: list[Connection] = []

    with open(path, encoding="utf-8") as map_file:
        lines = list(enumerate(map_file, start=1))
    last_line_no = lines[-1][0] if lines else 0

    for line_no, raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, args, metadata = _split(line_no, line)
        if key == "nb_drones":
            if len(args) != 1:
                raise MapFileError(line_no, "nb_drones expects one number")
            nb_drones = _int(line_no, args[0])
        elif key in ZONE_KEYS:
            zone = _zone(line_no, key, args, metadata)
            if zone.name in zones:
                raise MapFileError(line_no, f"duplicate zone '{zone.name}'")
            zones[zone.name] = zone
            if key == "start_hub":
                start = zone.name
            elif key == "end_hub":
                end = zone.name
        elif key == "connection":
            connection = _connection(line_no, args, metadata)
            _check_connection(line_no, connection, zones, connections)
            connections.append(connection)
        else:
            raise MapFileError(line_no, f"unknown key '{key}'")

    if nb_drones is None:
        raise MapFileError(last_line_no, "missing nb_drones")
    if start is None:
        raise MapFileError(last_line_no, "missing start_hub")
    if end is None:
        raise MapFileError(last_line_no, "missing end_hub")
    for name in (start, end):
        zone = zones[name]
        zones[name] = Zone(
            zone.name, zone.x, zone.y, zone.zone_type, zone.color, nb_drones
        )
    return FlyMap(nb_drones, start, end, zones, connections)


def _split(
    line_no: int, line: str
) -> tuple[str, list[str], dict[str, str]]:
    """Split ``key: args [name=value ...]``.

    Args:
        line_no: Line number, for errors.
        line: The stripped line.

    Returns:
        The key, the arguments, and the metadata.

    Raises:
        MapFileError: If there is no ``:`` or the metadata is malformed.
    """
    key, sep, rest = line.partition(":")
    if not sep:
        raise MapFileError(line_no, f"invalid line '{line}'")
    args_text, _, metadata_text = rest.partition("[")
    metadata: dict[str, str] = {}
    for item in metadata_text.rstrip("]").split():
        name, eq, value = item.partition("=")
        if not eq:
            raise MapFileError(line_no, f"invalid metadata '{item}'")
        metadata[name] = value
    return key.strip(), args_text.split(), metadata


def _int(line_no: int, value: str) -> int:
    """Convert ``value`` to an int, or raise MapFileError."""
    try:
        return int(value)
    except ValueError:
        raise MapFileError(
            line_no, f"expected an integer, got '{value}'"
        ) from None


def _zone(
    line_no: int, key: str, args: list[str], metadata: dict[str, str]
) -> Zone:
    """Build a zone from a ``start_hub``/``hub``/``end_hub`` line."""
    if len(args) != 3:
        raise MapFileError(line_no, f"{key} expects: <name> <x> <y>")
    name, x, y = args
    if "-" in name:
        raise MapFileError(line_no, f"zone name '{name}' must not contain '-'")
    try:
        zone_type = ZoneType(metadata.get("zone", "normal"))
    except ValueError:
        raise MapFileError(
            line_no, f"invalid zone type '{metadata['zone']}'"
        ) from None
    max_drones = 1
    if key == "hub" and "max_drones" in metadata:
        max_drones = _int(line_no, metadata["max_drones"])
    return Zone(
        name,
        _int(line_no, x),
        _int(line_no, y),
        zone_type,
        metadata.get("color"),
        max_drones,
    )


def _connection(
    line_no: int, args: list[str], metadata: dict[str, str]
) -> Connection:
    """Build a connection from a ``connection`` line."""
    if len(args) != 1 or args[0].count("-") != 1:
        raise MapFileError(line_no, "connection expects: <zone1>-<zone2>")
    a, b = args[0].split("-")
    capacity = _int(line_no, metadata.get("max_link_capacity", "1"))
    return Connection(a, b, capacity)


def _check_connection(
    line_no: int,
    connection: Connection,
    zones: dict[ZoneName, Zone],
    connections: list[Connection],
) -> None:
    """Reject a connection that does not fit the zones read so far."""
    for name in (connection.a, connection.b):
        if name not in zones:
            raise MapFileError(line_no, f"unknown zone '{name}'")
    if connection.a == connection.b:
        raise MapFileError(
            line_no, f"zone '{connection.a}' cannot connect to itself"
        )
    if any(other.link == connection.link for other in connections):
        raise MapFileError(
            line_no, f"duplicate connection {connection.name}"
        )
