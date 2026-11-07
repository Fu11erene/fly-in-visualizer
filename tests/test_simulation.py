"""Tests for the positions and counts rebuilt by simulation.py."""

from simulation import InFlight, simulate
from tests.helpers import N, R, link, make_map, turns


def test_turn_zero_is_all_at_start() -> None:
    """S1: before turn 1, every drone is at start."""
    fly_map = make_map({"a": N}, ["s-a", "a-e"])
    [state] = simulate(fly_map, [])
    assert state.turn == 0
    assert state.positions == {1: "s", 2: "s"}
    assert state.zone_counts["s"] == 2


def test_unlisted_drone_stays() -> None:
    """S2: a drone missing from a line stays where it was."""
    fly_map = make_map({"a": N}, ["s-a", "a-e"])
    states = simulate(fly_map, turns("D1-a", "D1-e D2-a"))
    assert states[1].positions == {1: "a", 2: "s"}
    assert states[2].positions == {1: "e", 2: "a"}


def test_waiting_drone_counts_in_zone() -> None:
    """S3: a waiting drone fills its zone but uses no link."""
    fly_map = make_map({"a": N}, ["s-a", "a-e"], nb_drones=1)
    states = simulate(fly_map, turns("D1-a", "", "D1-e"))
    assert states[2].zone_counts["a"] == 1
    assert states[2].link_counts == {}
    assert states[2].used_links == set()


def test_move_uses_link_in_either_direction() -> None:
    """S4: a move uses its link, whichever way it was written."""
    fly_map = make_map({"a": N}, ["a-s", "a-e"], nb_drones=1)
    states = simulate(fly_map, turns("D1-a"))
    assert states[1].link_counts == {link("s", "a"): 1}
    assert states[1].used_links == {link("s", "a")}


def test_restricted_entry_and_landing() -> None:
    """S5: entering uses the link only; landing fills the zone only."""
    fly_map = make_map({"r": R}, ["s-r", "r-e"], nb_drones=1)
    sr = fly_map.connections[0]
    states = simulate(fly_map, turns("D1-s-r", "D1-r"))
    assert states[1].positions == {1: InFlight(sr, "r")}
    assert states[1].zone_counts.get("r", 0) == 0
    assert states[1].zone_counts.get("s", 0) == 0
    assert states[1].link_counts == {link("s", "r"): 1}
    assert states[2].zone_counts["r"] == 1
    assert states[2].link_counts == {}


def test_landing_and_entry_share_turn() -> None:
    """S6: a landing does not use the link another drone enters."""
    fly_map = make_map({"r": R}, ["s-r", "r-e"])
    states = simulate(fly_map, turns("D1-s-r", "D1-r D2-s-r"))
    assert states[2].link_counts == {link("s", "r"): 1}


def test_delivered_drone_stays_at_end() -> None:
    """S7: a drone at end is counted there on every later turn."""
    fly_map = make_map({"a": N}, ["s-a", "a-e", "s-e"])
    states = simulate(fly_map, turns("D1-e", "D2-a", "D2-e"))
    assert states[2].zone_counts["e"] == 1
    assert states[3].zone_counts["e"] == 2
