"""Playback clock: which turn is shown, and how far into the move."""

import math

SPEEDS: tuple[float, ...] = (0.5, 1.0, 2.0, 4.0)
"""Speeds the player offers; at 1.0 one turn takes one second."""


class Player:
    """Video-player style control over the turns of a replay.

    ``time`` runs from 0 to ``last_turn``; ``1.5`` is halfway through
    the move from turn 1 to turn 2.
    """

    def __init__(self, last_turn: int) -> None:
        """Start paused on turn 0 at 1x.

        Args:
            last_turn: The last turn of the replay; 0 if there is none.
        """
        self.last_turn = last_turn
        self.time = 0.0
        self.playing = False
        self.speed = 1.0

    @property
    def from_turn(self) -> int:
        """The turn the current move starts from."""
        return math.floor(self.time)

    @property
    def shown_turn(self) -> int:
        """The turn the current move leads to; its counts are shown."""
        return math.ceil(self.time)

    @property
    def alpha(self) -> float:
        """How far into the current move, from 0 to 1."""
        return self.time - self.from_turn

    def toggle(self) -> None:
        """Play or pause; playing from the last turn restarts."""
        if not self.playing and self.time >= self.last_turn:
            self.time = 0.0
        self.playing = not self.playing

    def step(self, delta: int) -> None:
        """Go ``delta`` whole turns forward (or back if negative).

        From the middle of a move, one step forward reaches the turn the
        move leads to, and one step back the turn it started from.

        Args:
            delta: Number of turns; negative goes back.
        """
        if delta > 0:
            self.seek(math.floor(self.time) + delta)
        elif delta < 0:
            self.seek(math.ceil(self.time) + delta)

    def seek(self, turn: int) -> None:
        """Jump to ``turn``, kept within 0 and ``last_turn``.

        Args:
            turn: The turn to show.
        """
        self.time = float(min(max(turn, 0), self.last_turn))

    def set_speed(self, speed: float) -> None:
        """Change the playback speed.

        Args:
            speed: Turns per second.
        """
        self.speed = speed

    def update(self, dt: float) -> None:
        """Advance the clock while playing; stop on the last turn.

        Args:
            dt: Seconds since the previous update.
        """
        if not self.playing:
            return
        self.time += dt * self.speed
        if self.time >= self.last_turn:
            self.time = float(self.last_turn)
            self.playing = False
