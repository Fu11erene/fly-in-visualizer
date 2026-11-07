"""Tests for player.py."""

import pytest

from player import Player


def playing(last_turn: int) -> Player:
    """A player that has just started playing."""
    player = Player(last_turn)
    player.toggle()
    return player


def test_update_advances_time() -> None:
    """P1: playing for half a second goes halfway to turn 1."""
    player = playing(3)
    player.update(0.5)
    assert player.time == 0.5
    assert player.from_turn == 0
    assert player.shown_turn == 1
    assert player.alpha == 0.5


def test_paused_does_not_move() -> None:
    """P2: update does nothing while paused."""
    player = Player(3)
    player.update(1.0)
    assert player.time == 0.0


def test_speed() -> None:
    """P3: at 2x, half a second is a whole turn."""
    player = playing(3)
    player.set_speed(2.0)
    player.update(0.5)
    assert player.time == 1.0


def test_stops_at_last_turn() -> None:
    """P4: playing never goes past the last turn, and then stops."""
    player = playing(2)
    player.update(10)
    assert player.time == 2.0
    assert player.playing is False


def test_play_at_end_restarts() -> None:
    """P5: pressing play on the last turn starts again from turn 0."""
    player = playing(2)
    player.update(10)
    player.toggle()
    assert player.time == 0.0
    assert player.playing is True


def test_step() -> None:
    """P6: steps go to the next or previous whole turn."""
    player = Player(3)
    player.seek(1)
    player.time = 1.4
    player.step(1)
    assert player.time == 2.0
    player.time = 1.4
    player.step(-1)
    assert player.time == 1.0
    player.step(-1)
    assert player.time == 0.0


@pytest.mark.parametrize(
    ("turn", "expected"),
    [
        pytest.param(-3, 0.0, id="P7a"),
        pytest.param(99, 3.0, id="P7b"),
        pytest.param(2, 2.0, id="P7c"),
    ],
)
def test_seek_is_clamped(turn: int, expected: float) -> None:
    """P7: seeking outside the turns lands on the nearest one."""
    player = Player(3)
    player.seek(turn)
    assert player.time == expected
    player.seek(0)
    player.step(turn)
    assert player.time == expected


def test_seek_keeps_playing_state() -> None:
    """P8: seeking and stepping neither start nor stop playback."""
    player = playing(3)
    player.seek(2)
    player.step(-1)
    assert player.playing is True
    player.toggle()
    player.seek(1)
    assert player.playing is False


def test_no_turns() -> None:
    """P9: a replay with only turn 0 never fails."""
    player = Player(0)
    player.toggle()
    player.update(1.0)
    player.step(1)
    player.seek(5)
    assert player.time == 0.0
    assert player.shown_turn == 0
    assert player.alpha == 0.0
