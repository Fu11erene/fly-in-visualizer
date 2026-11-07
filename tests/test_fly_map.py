"""Tests for fly_map.py."""

from pathlib import Path

import pytest

from fly_map import Connection, FlyMap, MapFileError, ZoneType, parse_map

SIMPLE_FORK = """\
# Easy Level 2: Simple fork with two paths
nb_drones: 4

start_hub: start 0 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: path_a 2 1 [color=blue]
hub: path_b 2 -1 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-junction [max_link_capacity=2]
connection: junction-path_a
connection: junction-path_b
connection: path_a-goal
connection: path_b-goal
"""


def parse(tmp_path: Path, content: str) -> FlyMap:
    """Write ``content`` to a map file and parse it."""
    path = tmp_path / "map.txt"
    path.write_text(content)
    return parse_map(str(path))


def test_simple_fork(tmp_path: Path) -> None:
    """M1: a shipped map is read with its zones and connections."""
    fly_map = parse(tmp_path, SIMPLE_FORK)
    assert fly_map.nb_drones == 4
    assert fly_map.start == "start"
    assert fly_map.end == "goal"
    assert fly_map.zones["junction"].max_drones == 2
    assert fly_map.zones["junction"].color == "yellow"
    assert fly_map.zones["path_b"].y == -1
    assert fly_map.connections[0] == Connection("start", "junction", 2)
    assert fly_map.connections[1].max_link_capacity == 1


def test_start_and_end_hold_every_drone(tmp_path: Path) -> None:
    """M2: start and end hold nb_drones, whatever max_drones says."""
    fly_map = parse(
        tmp_path,
        "nb_drones: 3\n"
        "start_hub: s 0 0 [max_drones=1]\n"
        "end_hub: e 1 0 [max_drones=x]\n",
    )
    assert fly_map.zones["s"].max_drones == 3
    assert fly_map.zones["e"].max_drones == 3


def test_zone_type(tmp_path: Path) -> None:
    """M3: zone= sets the type; it defaults to normal."""
    fly_map = parse(
        tmp_path,
        "nb_drones: 1\n"
        "start_hub: s 0 0\n"
        "hub: r 1 0 [zone=restricted]\n"
        "end_hub: e 2 0\n",
    )
    assert fly_map.zones["r"].zone_type is ZoneType.RESTRICTED
    assert fly_map.zones["s"].zone_type is ZoneType.NORMAL


def test_skips_comments_and_blank_lines(tmp_path: Path) -> None:
    """M4: comment lines and blank lines are ignored."""
    fly_map = parse(
        tmp_path,
        "# comment\n\n  # comment\nnb_drones: 2\n\n"
        "start_hub: s 0 0\nend_hub: e 1 0\n",
    )
    assert fly_map.nb_drones == 2
    assert list(fly_map.zones) == ["s", "e"]


def test_connection_lookup(tmp_path: Path) -> None:
    """M5: connections are found in either direction."""
    fly_map = parse(tmp_path, SIMPLE_FORK)
    start_junction = fly_map.connections[0]
    assert fly_map.connection_between("junction", "start") is start_junction
    assert fly_map.connection_named("junction-start") is start_junction
    assert fly_map.connection_named("start-junction") is start_junction
    assert fly_map.connection_between("start", "goal") is None
    assert fly_map.connection_named("start-goal") is None
    assert fly_map.connection_named("start") is None


@pytest.mark.parametrize(
    "line",
    [
        pytest.param("hub: a 0", id="M6a"),
        pytest.param("foo: x", id="M6b"),
        pytest.param("hub: a x 0", id="M6c"),
    ],
)
def test_unreadable_line(tmp_path: Path, line: str) -> None:
    """M6: a line that cannot be read reports its line number."""
    content = f"nb_drones: 1\nstart_hub: s 0 0\n{line}\nend_hub: e 1 0\n"
    with pytest.raises(MapFileError, match=r"^line 3:"):
        parse(tmp_path, content)


def test_missing_start(tmp_path: Path) -> None:
    """M7: a map without start_hub is rejected."""
    with pytest.raises(MapFileError, match="start_hub"):
        parse(tmp_path, "nb_drones: 1\nend_hub: e 1 0\n")
