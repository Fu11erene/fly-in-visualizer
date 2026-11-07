"""The window and its main loop."""

import pygame

from colors import BACKGROUND
from fly_map import FlyMap
from layout import MapLayout
from panel import PANEL_HEIGHT, Panel
from player import SPEEDS, Player
from replay import TurnRecord
from simulation import TurnState
from view import draw_map

WINDOW_SIZE = (1280, 800)
FPS = 60
SPEED_KEYS = (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4)


def run(
    fly_map: FlyMap,
    records: list[TurnRecord],
    states: list[TurnState],
    title: str,
) -> None:
    """Open the window and replay until it is closed.

    Args:
        fly_map: The map.
        records: The output, one record per turn from turn 1.
        states: ``simulate(fly_map, records)``.
        title: The window title.
    """
    pygame.init()
    try:
        _loop(fly_map, records, states, title)
    finally:
        pygame.quit()


def _loop(
    fly_map: FlyMap,
    records: list[TurnRecord],
    states: list[TurnState],
    title: str,
) -> None:
    """Handle input and draw frames until the user quits."""
    screen = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
    pygame.display.set_caption(title)
    font = pygame.font.Font(None, 20)
    panel = Panel(font)
    player = Player(len(states) - 1)
    violation_turns = [state.turn for state in states if state.violations]
    total_violations = sum(len(state.violations) for state in states)
    clock = pygame.time.Clock()

    while True:
        dt = clock.tick(FPS) / 1000
        width, height = screen.get_size()
        map_height = max(height - PANEL_HEIGHT, 0)
        panel.layout(pygame.Rect(0, map_height, width, PANEL_HEIGHT))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    return
                _handle_key(event.key, player)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                panel.handle_mouse_down(event.pos, player)
            elif event.type == pygame.MOUSEMOTION and event.buttons[0]:
                panel.handle_mouse_drag(event.pos, player)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                panel.handle_mouse_up()
        player.update(dt)

        screen.fill(BACKGROUND)
        layout = MapLayout(fly_map, 0, 0, width, map_height)
        mouse = pygame.mouse.get_pos()
        draw_map(
            screen,
            layout,
            fly_map,
            states[player.from_turn],
            states[player.shown_turn],
            player.alpha,
            font,
            hover=mouse if mouse[1] < map_height else None,
        )
        shown = player.shown_turn
        panel.draw(
            screen,
            player,
            records[shown - 1] if shown > 0 else None,
            states[shown],
            violation_turns,
            total_violations,
        )
        pygame.display.flip()


def _handle_key(key: int, player: Player) -> None:
    """Apply a playback key."""
    if key == pygame.K_SPACE:
        player.toggle()
    elif key == pygame.K_LEFT:
        player.step(-1)
    elif key == pygame.K_RIGHT:
        player.step(1)
    elif key == pygame.K_HOME:
        player.seek(0)
    elif key == pygame.K_END:
        player.seek(player.last_turn)
    elif key in SPEED_KEYS:
        player.set_speed(SPEEDS[SPEED_KEYS.index(key)])
