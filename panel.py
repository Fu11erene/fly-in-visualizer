"""The control panel under the map: seek bar, buttons, output, help."""

from collections.abc import Callable

import pygame

from colors import BACKGROUND, DIM_TEXT, ERROR, HIGHLIGHT, OK, TEXT
from player import SPEEDS, Player
from replay import TurnRecord, colored_segments
from simulation import TurnState

PANEL_HEIGHT = 190
HELP = (
    "SPACE play/pause | LEFT/RIGHT step | HOME/END first/last | "
    "1-4 speed | click bar to seek | Q/ESC quit"
)
BUTTON = (50, 50, 50)
BUTTON_ACTIVE = (90, 90, 90)
BAR = (60, 60, 60)
BAR_FILL = (224, 0, 68)


class Panel:
    """Draws the panel and turns mouse input into player commands."""

    def __init__(self, font: pygame.font.Font) -> None:
        """Create the panel; call ``layout`` before drawing.

        Args:
            font: Font for every text in the panel.
        """
        self._font = font
        self._rect = pygame.Rect(0, 0, 0, 0)
        self._bar = pygame.Rect(0, 0, 0, 0)
        self._buttons: list[tuple[pygame.Rect, str]] = []
        self._dragging = False

    def layout(self, rect: pygame.Rect) -> None:
        """Place the seek bar and buttons inside ``rect``.

        Args:
            rect: The panel's area; call again when the window resizes.
        """
        self._rect = rect
        x, y = rect.left + 20, rect.top
        self._bar = pygame.Rect(
            x + 120, y + 16, max(rect.width - 160, 10), 8
        )
        self._buttons = []
        bx = x
        for action in ("first", "back", "play", "forward", "last"):
            self._buttons.append((pygame.Rect(bx, y + 40, 40, 30), action))
            bx += 46
        bx += 30
        for speed in SPEEDS:
            self._buttons.append(
                (pygame.Rect(bx, y + 40, 52, 30), f"speed:{speed}")
            )
            bx += 58

    def draw(
        self,
        surface: pygame.Surface,
        player: Player,
        record: TurnRecord | None,
        state: TurnState,
        violation_turns: list[int],
        total_violations: int,
    ) -> None:
        """Draw the panel for the turn the player shows.

        Args:
            surface: Where to draw.
            player: The playback state.
            record: The output line of the shown turn; None on turn 0.
            state: The shown turn's state, for its violations.
            violation_turns: Every turn with a violation, for the marks
                on the seek bar.
            total_violations: Violations over the whole replay.
        """
        pygame.draw.rect(surface, BACKGROUND, self._rect)
        pygame.draw.line(
            surface, BAR, self._rect.topleft, self._rect.topright
        )
        self._draw_seek_bar(surface, player, violation_turns)
        for rect, action in self._buttons:
            self._draw_button(surface, rect, action, player)

        left, top = self._rect.left + 20, self._rect.top
        line = pygame.Rect(left, top + 84, self._rect.width - 40, 28)
        pygame.draw.rect(surface, (0, 0, 0), line)
        pygame.draw.rect(surface, BAR, line, 1)
        segments: list[tuple[str, tuple[int, int, int] | None]] = [
            (f"turn {player.shown_turn} $ ", DIM_TEXT)
        ]
        if record is not None:
            segments += colored_segments(record.raw)
        self._draw_segments(surface, segments, line.inflate(-12, 0))

        status = pygame.Rect(left, top + 120, self._rect.width - 40, 24)
        if state.violations:
            text = " / ".join(v.message for v in state.violations)
            self._draw_segments(surface, [(text, ERROR)], status)
        elif total_violations == 0:
            self._draw_segments(surface, [("No violations", OK)], status)
        else:
            self._draw_segments(
                surface,
                [(f"{total_violations} violations in other turns", ERROR)],
                status,
            )
        help_rect = pygame.Rect(left, top + 152, self._rect.width - 40, 24)
        self._draw_segments(surface, [(HELP, DIM_TEXT)], help_rect)

    def handle_mouse_down(
        self, pos: tuple[int, int], player: Player
    ) -> None:
        """Press a button, or start seeking on the bar.

        Args:
            pos: Mouse position.
            player: The player to control.
        """
        if self._bar.inflate(0, 20).collidepoint(pos):
            self._dragging = True
            self._seek(pos, player)
            return
        for rect, action in self._buttons:
            if rect.collidepoint(pos):
                _ACTIONS[action.split(":")[0]](player, action)
                return

    def handle_mouse_drag(
        self, pos: tuple[int, int], player: Player
    ) -> None:
        """Keep seeking while the bar is dragged.

        Args:
            pos: Mouse position.
            player: The player to control.
        """
        if self._dragging:
            self._seek(pos, player)

    def handle_mouse_up(self) -> None:
        """Stop dragging the bar."""
        self._dragging = False

    def _seek(self, pos: tuple[int, int], player: Player) -> None:
        """Jump to the turn nearest to ``pos`` on the bar."""
        fraction = (pos[0] - self._bar.left) / self._bar.width
        player.seek(round(fraction * player.last_turn))

    def _turn_x(self, turn: float, last_turn: int) -> int:
        """The x position of ``turn`` on the bar."""
        if last_turn == 0:
            return self._bar.left
        return int(self._bar.left + self._bar.width * turn / last_turn)

    def _draw_seek_bar(
        self,
        surface: pygame.Surface,
        player: Player,
        violation_turns: list[int],
    ) -> None:
        """Draw the turn counter, the bar, its marks and its knob."""
        label = self._font.render(
            f"{player.shown_turn} / {player.last_turn}", True, TEXT
        )
        surface.blit(
            label,
            label.get_rect(
                midleft=(self._rect.left + 20, self._bar.centery)
            ),
        )
        pygame.draw.rect(surface, BAR, self._bar, border_radius=4)
        knob_x = self._turn_x(player.time, player.last_turn)
        filled = pygame.Rect(
            self._bar.left, self._bar.top, knob_x - self._bar.left, 8
        )
        pygame.draw.rect(surface, BAR_FILL, filled, border_radius=4)
        for turn in violation_turns:
            x = self._turn_x(turn, player.last_turn)
            pygame.draw.rect(
                surface, ERROR, (x - 2, self._bar.top - 6, 4, 20)
            )
        pygame.draw.circle(
            surface, (255, 255, 255), (knob_x, self._bar.centery), 7
        )

    def _draw_button(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        action: str,
        player: Player,
    ) -> None:
        """Draw one button, with a drawn icon or a speed label."""
        active = action == f"speed:{player.speed}"
        pygame.draw.rect(
            surface, BUTTON_ACTIVE if active else BUTTON, rect,
            border_radius=4,
        )
        if active:
            pygame.draw.rect(surface, BAR_FILL, rect, 2, border_radius=4)
        if action.startswith("speed:"):
            speed = float(action.split(":")[1])
            text = f"{speed:g}x"
            image = self._font.render(text, True, TEXT)
            surface.blit(image, image.get_rect(center=rect.center))
            return
        _ICONS[action](surface, rect, player)

    def _draw_segments(
        self,
        surface: pygame.Surface,
        segments: list[tuple[str, tuple[int, int, int] | None]],
        rect: pygame.Rect,
    ) -> None:
        """Draw colored runs of text left to right, clipped to ``rect``."""
        previous_clip = surface.get_clip()
        surface.set_clip(rect)
        x = rect.left
        for text, color in segments:
            image = self._font.render(text, True, color or TEXT)
            surface.blit(image, image.get_rect(midleft=(x, rect.centery)))
            x += image.get_width()
        surface.set_clip(previous_clip)


def _triangle(
    surface: pygame.Surface, cx: int, cy: int, size: int, direction: int
) -> None:
    """A filled triangle pointing right (1) or left (-1)."""
    pygame.draw.polygon(
        surface,
        TEXT,
        [
            (cx - direction * size, cy - size),
            (cx - direction * size, cy + size),
            (cx + direction * size, cy),
        ],
    )


def _icon_first(
    surface: pygame.Surface, rect: pygame.Rect, player: Player
) -> None:
    cx, cy = rect.center
    pygame.draw.rect(surface, TEXT, (cx - 9, cy - 7, 3, 14))
    _triangle(surface, cx + 2, cy, 7, -1)


def _icon_back(
    surface: pygame.Surface, rect: pygame.Rect, player: Player
) -> None:
    _triangle(surface, rect.centerx, rect.centery, 7, -1)


def _icon_play(
    surface: pygame.Surface, rect: pygame.Rect, player: Player
) -> None:
    cx, cy = rect.center
    if player.playing:
        pygame.draw.rect(surface, HIGHLIGHT, (cx - 7, cy - 8, 5, 16))
        pygame.draw.rect(surface, HIGHLIGHT, (cx + 2, cy - 8, 5, 16))
    else:
        _triangle(surface, cx + 1, cy, 8, 1)


def _icon_forward(
    surface: pygame.Surface, rect: pygame.Rect, player: Player
) -> None:
    _triangle(surface, rect.centerx, rect.centery, 7, 1)


def _icon_last(
    surface: pygame.Surface, rect: pygame.Rect, player: Player
) -> None:
    cx, cy = rect.center
    _triangle(surface, cx - 2, cy, 7, 1)
    pygame.draw.rect(surface, TEXT, (cx + 6, cy - 7, 3, 14))


_ICONS: dict[
    str, Callable[[pygame.Surface, pygame.Rect, Player], None]
] = {
    "first": _icon_first,
    "back": _icon_back,
    "play": _icon_play,
    "forward": _icon_forward,
    "last": _icon_last,
}

_ACTIONS: dict[str, Callable[[Player, str], None]] = {
    "first": lambda player, _: player.seek(0),
    "back": lambda player, _: player.step(-1),
    "play": lambda player, _: player.toggle(),
    "forward": lambda player, _: player.step(1),
    "last": lambda player, _: player.seek(player.last_turn),
    "speed": lambda player, action: player.set_speed(
        float(action.split(":")[1])
    ),
}
