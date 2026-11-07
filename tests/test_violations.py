"""Tests for the rule violations found by simulation.py."""

from pathlib import Path

import pytest

from fly_map import FlyMap, Zone, ZoneType, parse_map
from replay import read_output
from simulation import InFlight, TurnState, ViolationKind, simulate
from tests.helpers import B, N, R, link, make_map, turns

K = ViolationKind
FIXTURES = Path(__file__).parent / "fixtures"
MAPS = sorted((FIXTURES / "maps").rglob("*.txt"))


def kinds(state: TurnState) -> list[ViolationKind]:
    """The kinds of violation found on a turn."""
    return [violation.kind for violation in state.violations]


def test_zone_full() -> None:
    """V1: more drones in a zone than max_drones."""
    fly_map = make_map({"a": N}, ["s-a", "a-e"], link_capacities={"s-a": 2})
    states = simulate(fly_map, turns("D1-a D2-a", "D1-e", "D2-e"))
    assert kinds(states[1]) == [K.ZONE_FULL]
    [violation] = states[1].violations
    assert violation.zone == "a"
    assert violation.message == "a: 2/1 (over max_drones)"


def test_link_full() -> None:
    """V2: more drones on a link than max_link_capacity."""
    fly_map = make_map({"a": N}, ["s-a", "a-e"], capacities={"a": 2})
    states = simulate(fly_map, turns("D1-a D2-a", "D1-e", "D2-e"))
    assert kinds(states[1]) == [K.LINK_FULL]
    [violation] = states[1].violations
    assert violation.link == link("s", "a")
    assert violation.message == "s-a: 2/1 (over max_link_capacity)"


def test_no_connection() -> None:
    """V3: a move between zones that are not connected."""
    fly_map = make_map({"a": N}, ["s-a", "a-e"], nb_drones=1)
    [_, state] = simulate(fly_map, turns("D1-e"))
    assert kinds(state) == [K.NO_CONNECTION]
    assert state.violations[0].drone == 1
    assert state.positions == {1: "e"}


def test_no_connection_in_flight() -> None:
    """V3a: flying onto a connection that does not touch the zone."""
    fly_map = make_map({"a": N, "r": R}, ["s-a", "a-r", "r-e"], nb_drones=1)
    states = simulate(fly_map, turns("D1-a-r", "D1-r", "D1-e"))
    assert kinds(states[1]) == [K.NO_CONNECTION]
    assert kinds(states[2]) == kinds(states[3]) == []


def test_blocked() -> None:
    """V4: entering a blocked zone."""
    fly_map = make_map({"x": B}, ["s-x", "x-e"], nb_drones=1)
    states = simulate(fly_map, turns("D1-x", "D1-e"))
    assert kinds(states[1]) == [K.BLOCKED]
    assert states[1].violations[0].zone == "x"
    assert states[1].violations[0].drone == 1


def test_restricted_skipped() -> None:
    """V5: entering a restricted zone in one turn."""
    fly_map = make_map({"r": R}, ["s-r", "r-e"], nb_drones=1)
    states = simulate(fly_map, turns("D1-r", "D1-e"))
    assert kinds(states[1]) == [K.RESTRICTED_SKIPPED]
    assert states[1].violations[0].zone == "r"


def test_not_landed() -> None:
    """V6: a drone on a connection that does not land the next turn."""
    fly_map = make_map({"r": R}, ["s-r", "r-e"], nb_drones=1)
    sr = fly_map.connections[0]
    states = simulate(fly_map, turns("D1-s-r", "", "D1-r", "D1-e"))
    assert kinds(states[2]) == [K.NOT_LANDED]
    assert states[2].violations[0].drone == 1
    assert states[2].positions == {1: InFlight(sr, "r")}
    assert kinds(states[3]) == kinds(states[4]) == []


def test_not_restricted() -> None:
    """V7: flying onto a connection that leads to a normal zone."""
    fly_map = make_map({"a": N}, ["s-a", "a-e"], nb_drones=1)
    states = simulate(fly_map, turns("D1-s-a", "D1-a", "D1-e"))
    assert kinds(states[1]) == [K.NOT_RESTRICTED]
    assert states[1].violations[0].link == link("s", "a")


def test_unknown_name() -> None:
    """V8: a name that is neither a zone nor a connection."""
    fly_map = make_map({"a": N}, ["s-a", "a-e"], nb_drones=1)
    states = simulate(fly_map, turns("D1-zz", "D1-a", "D1-e"))
    assert kinds(states[1]) == [K.UNKNOWN_NAME]
    assert states[1].positions == {1: "s"}


def test_unknown_drone() -> None:
    """V9: a drone ID outside 1..nb_drones."""
    fly_map = make_map({"a": N}, ["s-a", "a-e"], nb_drones=1)
    states = simulate(fly_map, turns("D1-a D9-a", "D1-e"))
    assert kinds(states[1]) == [K.UNKNOWN_DRONE]
    assert states[1].violations[0].drone is None
    assert states[1].zone_counts["a"] == 1


def test_duplicate_drone() -> None:
    """V10: the same drone twice on one line; the first one counts."""
    fly_map = make_map({"a": N}, ["s-a", "a-e"], nb_drones=1)
    states = simulate(fly_map, turns("D1-a D1-e", "D1-e"))
    assert kinds(states[1]) == [K.DUPLICATE_DRONE]
    assert states[1].positions == {1: "a"}


def test_moved_after_end() -> None:
    """V11: a drone that leaves end after reaching it."""
    fly_map = make_map({"a": N}, ["s-e", "a-e"], nb_drones=1)
    states = simulate(fly_map, turns("D1-e", "D1-a", "D1-e"))
    assert kinds(states[2]) == [K.MOVED_AFTER_END]
    assert kinds(states[3]) == []


def test_not_delivered() -> None:
    """V12: a drone not at end on the last turn."""
    fly_map = make_map({"a": N}, ["s-a", "a-e"])
    states = simulate(fly_map, turns("D1-a", "D1-e"))
    assert kinds(states[1]) == []
    assert kinds(states[2]) == [K.NOT_DELIVERED]
    assert states[2].violations[0].drone == 2


def test_empty_output_delivers_nobody() -> None:
    """V12a: with no turns at all, turn 0 reports every drone."""
    fly_map = make_map({"a": N}, ["s-a", "a-e"])
    [state] = simulate(fly_map, [])
    assert kinds(state) == [K.NOT_DELIVERED, K.NOT_DELIVERED]


@pytest.mark.parametrize(
    ("hubs", "links", "nb_drones", "lines"),
    [
        pytest.param(
            {"a": N}, ["s-a", "a-e"], 1, ["D1-a", "", "D1-e"], id="V13a"
        ),
        pytest.param(
            {"r": R}, ["s-r", "r-e"], 1, ["D1-s-r", "D1-r", "D1-e"], id="V13b"
        ),
        pytest.param(
            {"a": N},
            ["s-a", "a-e", "s-e"],
            2,
            ["D1-e", "D2-a", "D2-e"],
            id="V13c",
        ),
        pytest.param(
            {"r": R},
            ["s-r", "r-e"],
            2,
            ["D1-s-r", "D1-r D2-s-r", "D1-e D2-r", "D2-e"],
            id="V13d",
        ),
    ],
)
def test_valid_output_has_no_violation(
    hubs: dict[str, ZoneType],
    links: list[str],
    nb_drones: int,
    lines: list[str],
) -> None:
    """V13: a correct output reports nothing on any turn."""
    fly_map = make_map(hubs, links, nb_drones)
    for state in simulate(fly_map, turns(*lines)):
        assert state.violations == []


def test_restricted_end() -> None:
    """V13e: a restricted end is entered through its connection."""
    fly_map = make_map({"a": N}, ["s-a", "a-e"], nb_drones=1)
    zones = {**fly_map.zones, "e": Zone("e", 2, 0, R, None, 1)}
    fly_map = FlyMap(1, "s", "e", zones, fly_map.connections)
    for state in simulate(fly_map, turns("D1-a", "D1-a-e", "D1-e")):
        assert state.violations == []


@pytest.mark.parametrize(
    "map_path",
    [
        pytest.param(path, id=f"V20{chr(ord('a') + i)}")
        for i, path in enumerate(MAPS)
    ],
)
def test_fly_in_outputs_are_clean(map_path: Path) -> None:
    """V20: Fly-in's own output for every map has no violation."""
    relative = map_path.relative_to(FIXTURES / "maps")
    output_path = FIXTURES / "outputs" / relative
    fly_map = parse_map(str(map_path))
    states = simulate(fly_map, read_output(str(output_path)))
    found = [(s.turn, v.message) for s in states for v in s.violations]
    assert found == []
